"""백그라운드 변환 워커. UI 스레드를 막지 않도록 QThread에서 실행된다."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

import os

from core.document import build_convert_command, expected_output, find_soffice
from core.errors import (
    friendly_document_error, friendly_ffmpeg_error, friendly_image_error,
)
from core.ffmpeg_tools import Tools, probe_duration
from core.image import convert_image
from core.media import (
    build_command, build_image_sequence_command, segment_duration, write_concat_file,
)
from core.registry import MediaKind, kind_of

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class ConversionWorker(QObject):
    """jobs: list of (input_path, output_path, out_ext)."""

    progress = Signal(float)          # 전체 진행률 0.0~1.0
    fileProgress = Signal(float)      # 현재 파일 진행률 0.0~1.0
    status = Signal(str)              # 상태 텍스트
    finished = Signal(bool, str)      # (성공여부, 메시지)

    def __init__(self, jobs, options, tools: Tools, soffice: str | None = None):
        super().__init__()
        self._jobs = jobs
        self._opt = options
        self._tools = tools
        self._soffice = soffice
        self._cancel = False

    @Slot()
    def cancel(self):
        self._cancel = True

    @Slot()
    def run(self):
        total = len(self._jobs)
        if total == 0:
            self.finished.emit(False, "변환할 파일이 없습니다.")
            return
        try:
            for i, (inp, out, ext) in enumerate(self._jobs):
                if self._cancel:
                    self.finished.emit(False, "사용자가 취소했습니다.")
                    return
                self.status.emit(f"변환 중 ({i + 1}/{total}): {Path(out).name}")
                self._convert_one(i, total, inp, out, ext)
            self.progress.emit(1.0)
            self.finished.emit(True, f"완료: {total}개 변환")
        except Exception as exc:  # noqa: BLE001 - 친화적 메시지를 그대로 전달
            self.finished.emit(False, str(exc))

    def _convert_one(self, index, total, inp, out, ext):
        self.fileProgress.emit(0.0)

        # 이미지 시퀀스 → 영상(C6): inp가 리스트
        if isinstance(inp, (list, tuple)):
            self._convert_sequence(index, total, list(inp), out, ext)
            return

        in_ext = Path(inp).suffix.lstrip(".")

        # 문서 → 문서(C7): LibreOffice
        if kind_of(in_ext) == MediaKind.DOCUMENT:
            self._convert_document(index, total, inp, out, ext)
            return

        # 입력이 이미지면 Pillow로 인프로세스 변환(C4, ffmpeg 불필요).
        # 영상→이미지(C5)는 입력이 영상이므로 아래 ffmpeg 경로로 간다.
        if kind_of(in_ext) == MediaKind.IMAGE:
            try:
                convert_image(inp, out, ext, self._opt)
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(friendly_image_error(exc, Path(inp).name)) from exc
            self.fileProgress.emit(1.0)
            self.progress.emit((index + 1) / total)
            return

        full = probe_duration(self._tools.ffprobe, inp)
        seg = segment_duration(full, self._opt)
        cmd = build_command(self._tools.ffmpeg, inp, out, ext, self._opt, seg)
        self._run_proc(cmd, seg, index, total, Path(inp).name)

    def _convert_sequence(self, index, total, images, out, ext):
        tmp = tempfile.mkdtemp(prefix="fc_seq_")
        try:
            concat = str(Path(tmp) / "list.txt")
            write_concat_file(images, self._opt.seconds_per_image, concat)
            seg = max(0.01, len(images) * self._opt.seconds_per_image)
            cmd = build_image_sequence_command(self._tools.ffmpeg, concat, out, ext, self._opt)
            self._run_proc(cmd, seg, index, total, Path(out).name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _convert_document(self, index, total, inp, out, ext):
        soffice = self._soffice or find_soffice()  # 없으면 SofficeNotFound → run()에서 처리
        name = Path(inp).name
        profile = tempfile.mkdtemp(prefix="fc_lo_")
        try:
            outdir = str(Path(out).parent)
            cmd = build_convert_command(soffice, inp, ext, outdir, profile)
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                creationflags=_NO_WINDOW, timeout=180,
            )
            produced = expected_output(inp, ext, outdir)
            if not Path(produced).exists():
                raise RuntimeError(friendly_document_error(proc.stdout + proc.stderr, name))
            if os.path.abspath(produced) != os.path.abspath(out):
                os.replace(produced, out)  # _dest_for가 _converted 등으로 바꾼 경우 맞춤
            self.fileProgress.emit(1.0)
            self.progress.emit((index + 1) / total)
        finally:
            shutil.rmtree(profile, ignore_errors=True)

    def _run_proc(self, cmd, seg, index, total, name):
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=_NO_WINDOW,
        )
        assert proc.stdout is not None
        err_lines: list[str] = []
        for line in proc.stdout:
            if self._cancel:
                proc.terminate()
                break
            frac = self._parse_progress(line, seg)
            if frac is not None:
                self.fileProgress.emit(min(frac, 1.0))
                self.progress.emit((index + min(frac, 1.0)) / total)
            elif line.strip() and "=" not in line:
                # -loglevel error 라서 진행률(key=value)이 아닌 줄은 오류 메시지
                err_lines.append(line.strip())
        proc.wait()
        if proc.returncode not in (0, None) and not self._cancel:
            raise RuntimeError(friendly_ffmpeg_error("\n".join(err_lines[-6:]), name))
        self.fileProgress.emit(1.0)

    @staticmethod
    def _parse_progress(line: str, seg_dur: float | None) -> float | None:
        line = line.strip()
        if not seg_dur or "=" not in line:
            return None
        key, _, value = line.partition("=")
        if key == "out_time_us":
            try:
                return float(value) / 1_000_000 / seg_dur
            except ValueError:
                return None
        if key == "out_time_ms":
            try:
                return float(value) / 1_000 / seg_dur
            except ValueError:
                return None
        return None
