"""백그라운드 변환 워커. UI 스레드를 막지 않도록 QThread에서 실행된다."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from core.ffmpeg_tools import Tools, probe_duration
from core.media import build_command, segment_duration

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class ConversionWorker(QObject):
    """jobs: list of (input_path, output_path, out_ext)."""

    progress = Signal(float)          # 전체 진행률 0.0~1.0
    status = Signal(str)              # 상태 텍스트
    finished = Signal(bool, str)      # (성공여부, 메시지)

    def __init__(self, jobs, options, tools: Tools):
        super().__init__()
        self._jobs = jobs
        self._opt = options
        self._tools = tools
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
                self.status.emit(f"변환 중 ({i + 1}/{total}): {Path(inp).name}")
                self._convert_one(i, total, inp, out, ext)
            self.progress.emit(1.0)
            self.finished.emit(True, f"완료: {total}개 파일 변환")
        except Exception as exc:  # noqa: BLE001 - UI에 그대로 전달
            self.finished.emit(False, f"오류: {exc}")

    def _convert_one(self, index, total, inp, out, ext):
        full = probe_duration(self._tools.ffprobe, inp)
        seg = segment_duration(full, self._opt)
        cmd = build_command(
            self._tools.ffmpeg, inp, out, ext, self._opt, seg
        )
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=_NO_WINDOW,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            if self._cancel:
                proc.terminate()
                break
            frac = self._parse_progress(line, seg)
            if frac is not None:
                overall = (index + min(frac, 1.0)) / total
                self.progress.emit(overall)
        proc.wait()
        if proc.returncode not in (0, None) and not self._cancel:
            raise RuntimeError(f"ffmpeg 종료 코드 {proc.returncode} ({Path(inp).name})")

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
