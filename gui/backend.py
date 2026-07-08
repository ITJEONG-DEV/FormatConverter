"""QML <-> Python 브리지. 파일 목록, 옵션, 변환 실행을 담당한다."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import (
    Property, QObject, QThread, QUrl, Signal, Slot,
)
from PySide6.QtGui import QDesktopServices

from core.document import SofficeNotFound, find_soffice
from core.estimate import estimate_output_bytes, format_size
from core.pdf import pdf_engine_available
from core.ffmpeg_tools import FFmpegNotFound, find_tools, probe_duration
from core.image import ImageOptions
from core.media import (
    AudioOptions, VideoOptions, VideoSequenceOptions, VideoToImageOptions,
)
from core.registry import (
    KIND_LABEL, MediaKind, is_supported_input, kind_of,
    output_categories_for, output_formats_for,
)
from gui.worker import ConversionWorker


class Backend(QObject):
    filesChanged = Signal()
    outputFormatsChanged = Signal()
    outputCategoriesChanged = Signal()
    outputKindChanged = Signal()
    inputKindChanged = Signal()
    progressChanged = Signal()
    fileProgressChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    estimatedSizeChanged = Signal()
    outputDirChanged = Signal()
    canOpenOutputChanged = Signal()

    def __init__(self):
        super().__init__()
        self._files: list[str] = []
        self._output_formats: list[str] = []
        self._output_format: str = ""
        self._output_kind: str = ""
        self._input_kind: str = ""
        self._categories: list = []
        self._selected_category: MediaKind | None = None
        self._progress: float = 0.0
        self._file_progress: float = 0.0
        self._status: str = "파일을 끌어다 놓으세요."
        self._busy: bool = False
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None
        self._durations: dict[str, float | None] = {}
        self._estimated_size: str = ""
        self._estimate_options: dict = {}
        self._output_dir: str = ""        # "" = 입력 파일과 같은 폴더
        self._last_output_dir: str = ""   # 마지막 변환 결과 폴더(열기용)
        self._can_open: bool = False

    # ---------- Properties ----------
    @Property(list, notify=filesChanged)
    def files(self):
        return [Path(f).name for f in self._files]

    @Property(list, notify=filesChanged)
    def fileInfos(self):
        """파일별 {name, size} — 목록 표시용(크기 포함)."""
        infos = []
        for f in self._files:
            try:
                size = os.path.getsize(f)
            except OSError:
                size = None
            infos.append({"name": Path(f).name, "size": format_size(size)})
        return infos

    @Property(str, notify=estimatedSizeChanged)
    def estimatedSize(self):
        return self._estimated_size

    @Property(str, notify=outputDirChanged)
    def outputDir(self):
        """저장 폴더 경로. 빈 문자열이면 입력 파일과 같은 폴더."""
        return self._output_dir

    @Property(bool, notify=canOpenOutputChanged)
    def canOpenOutput(self):
        return self._can_open

    @Slot("QUrl")
    def setOutputDir(self, url):
        path = url.toLocalFile() if hasattr(url, "toLocalFile") else str(url)
        if path:
            self._output_dir = path
            self.outputDirChanged.emit()

    @Slot()
    def clearOutputDir(self):
        self._output_dir = ""
        self.outputDirChanged.emit()

    @Slot()
    def openOutputFolder(self):
        if self._last_output_dir and os.path.isdir(self._last_output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_output_dir))

    @Property(list, notify=outputFormatsChanged)
    def outputFormats(self):
        return self._output_formats

    @Property(list, notify=outputCategoriesChanged)
    def outputCategories(self):
        """가능한 출력 종류: [{label, value}, ...] (영상/음원/이미지)."""
        return [{"label": KIND_LABEL[k], "value": k.value} for k in self._categories]

    @Property(str, notify=outputCategoriesChanged)
    def selectedCategory(self):
        return self._selected_category.value if self._selected_category else ""

    @Property(str, notify=outputKindChanged)
    def outputKind(self):
        """현재 선택된 출력 포맷의 종류: 'video' / 'audio' / 'image' / ''."""
        return self._output_kind

    @Property(str, notify=inputKindChanged)
    def inputKind(self):
        """추가된 입력 파일의 종류: 'video' / 'audio' / 'image' / ''."""
        return self._input_kind

    @Property(float, notify=progressChanged)
    def progress(self):
        return self._progress

    @Property(float, notify=fileProgressChanged)
    def fileProgress(self):
        return self._file_progress

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    # ---------- 내부 setter ----------
    def _set_status(self, text: str):
        self._status = text
        self.statusChanged.emit()

    def _set_progress(self, value: float):
        self._progress = value
        self.progressChanged.emit()

    def _set_file_progress(self, value: float):
        self._file_progress = value
        self.fileProgressChanged.emit()

    def _set_busy(self, value: bool):
        self._busy = value
        self.busyChanged.emit()

    def _set_output_kind(self):
        k = kind_of(self._output_format) if self._output_format else None
        self._output_kind = k.value if k else ""
        self.outputKindChanged.emit()

    def _set_input_kind(self):
        if self._files:
            k = kind_of(Path(self._files[0]).suffix.lstrip("."))
            self._input_kind = k.value if k else ""
        else:
            self._input_kind = ""
        self.inputKindChanged.emit()

    def _refresh_output_formats(self):
        prev = self._output_format
        if not self._files:
            self._categories = []
            self._selected_category = None
            self._output_formats = []
            self._output_format = ""
        else:
            first_ext = Path(self._files[0]).suffix.lstrip(".")
            self._categories = output_categories_for(first_ext)
            # 기존 선택 종류가 유효하면 유지, 아니면 기본(같은 종류) 선택
            if self._selected_category not in self._categories:
                self._selected_category = self._categories[0] if self._categories else None
            self._output_formats = output_formats_for(first_ext, self._selected_category)
            # 순서 변경·제거로 목록이 갱신돼도 기존 선택이 유효하면 유지
            if prev in self._output_formats:
                self._output_format = prev
            elif self._output_formats:
                self._output_format = self._output_formats[0]
            else:
                self._output_format = ""
        self._set_input_kind()
        self.outputCategoriesChanged.emit()
        self.outputFormatsChanged.emit()
        self._set_output_kind()
        self._recompute_estimate()

    @Slot(str)
    def setOutputCategory(self, value: str):
        target = next((k for k in self._categories if k.value == value), None)
        if target is None or target == self._selected_category:
            return
        self._selected_category = target
        if self._files:
            first_ext = Path(self._files[0]).suffix.lstrip(".")
            self._output_formats = output_formats_for(first_ext, target)
            self._output_format = self._output_formats[0] if self._output_formats else ""
        self.outputCategoriesChanged.emit()
        self.outputFormatsChanged.emit()
        self._set_output_kind()
        self._recompute_estimate()

    # ---------- 예상 크기 ----------
    def _recompute_estimate(self):
        est = None
        if self._files and self._output_format:
            durs = [self._durations.get(f) for f in self._files]
            est = estimate_output_bytes(self._output_format, self._estimate_options, durs)
        self._estimated_size = f"예상 출력 크기 ≈ {format_size(est)}" if est else ""
        self.estimatedSizeChanged.emit()

    def _probe_missing(self):
        """존재하는 입력 파일의 길이를 조회(캐시). ffprobe 헤더 읽기라 빠르다.

        존재하지 않는 경로(테스트 더미 등)는 건너뛰어 불필요한 subprocess를 피한다.
        """
        missing = [
            f for f in self._files
            if f not in self._durations and os.path.exists(f)
        ]
        if not missing:
            return
        try:
            tools = find_tools()
        except FFmpegNotFound:
            return
        if not tools.ffprobe:
            return
        for f in missing:
            self._durations[f] = probe_duration(tools.ffprobe, f)
        self._recompute_estimate()

    @Slot("QVariantMap")
    def updateEstimate(self, options):
        self._estimate_options = dict(options)
        self._recompute_estimate()

    # ---------- Slots ----------
    @Slot(list)
    def addUrls(self, urls):
        added = 0
        for u in urls:
            path = QUrl(u).toLocalFile() if isinstance(u, str) else u.toLocalFile()
            if not path:
                continue
            ext = Path(path).suffix.lstrip(".")
            if not is_supported_input(ext):
                continue
            if path not in self._files:
                self._files.append(path)
                added += 1
        if added:
            self.filesChanged.emit()
            self._refresh_output_formats()
            self._probe_missing()
            self._set_status(f"{len(self._files)}개 파일 준비됨.")
        elif not self._files:
            self._set_status("지원하지 않는 파일이거나 추가된 파일이 없습니다.")

    @Slot()
    def clearFiles(self):
        self._files.clear()
        self._durations.clear()
        self.filesChanged.emit()
        self._refresh_output_formats()
        self._set_progress(0.0)
        self._set_status("파일을 끌어다 놓으세요.")

    @Slot(int)
    def moveUp(self, index: int):
        if 0 < index < len(self._files):
            self._files[index - 1], self._files[index] = (
                self._files[index], self._files[index - 1],
            )
            self.filesChanged.emit()
            self._refresh_output_formats()

    @Slot(int)
    def moveDown(self, index: int):
        if 0 <= index < len(self._files) - 1:
            self._files[index + 1], self._files[index] = (
                self._files[index], self._files[index + 1],
            )
            self.filesChanged.emit()
            self._refresh_output_formats()

    @Slot(int)
    def removeAt(self, index: int):
        if 0 <= index < len(self._files):
            self._files.pop(index)
            self.filesChanged.emit()
            self._refresh_output_formats()
            if self._files:
                self._set_status(f"{len(self._files)}개 파일 준비됨.")
            else:
                self._set_progress(0.0)
                self._set_status("파일을 끌어다 놓으세요.")

    @Slot(str)
    def setOutputFormat(self, fmt: str):
        self._output_format = fmt
        self._set_output_kind()
        self._recompute_estimate()

    @Slot("QVariantMap")
    def start(self, options):
        if self._busy:
            return
        if not self._files:
            self._set_status("변환할 파일이 없습니다.")
            return

        out_ext = self._output_format or (
            self._output_formats[0] if self._output_formats else "mp3"
        )
        out_kind = kind_of(out_ext)
        in_kind = kind_of(Path(self._files[0]).suffix.lstrip("."))

        # 엔진 선택:
        #   문서→문서 = LibreOffice / 문서(pdf)→이미지 = pypdfium2
        #   이미지→이미지·pdf = Pillow(외부 엔진 불필요) / 그 외 = ffmpeg
        tools = None
        soffice = None
        if in_kind == MediaKind.DOCUMENT and out_kind == MediaKind.DOCUMENT:
            try:
                soffice = find_soffice()
            except SofficeNotFound as exc:
                self._set_status(str(exc))
                return
        elif in_kind == MediaKind.DOCUMENT and out_kind == MediaKind.IMAGE:
            if not pdf_engine_available():
                self._set_status("PDF 변환 라이브러리(pypdfium2)가 설치되어 있지 않습니다.")
                return
        elif in_kind == MediaKind.IMAGE and out_kind in (MediaKind.IMAGE, MediaKind.DOCUMENT):
            pass  # Pillow
        else:
            try:
                tools = find_tools()
            except FFmpegNotFound as exc:
                self._set_status(str(exc))
                return

        opt = self._build_options(options, out_kind, in_kind)

        if in_kind == MediaKind.IMAGE and out_kind in (MediaKind.VIDEO, MediaKind.DOCUMENT):
            # 모든 이미지(추가 순서) → 단일 결과 1개 (C6 슬라이드쇼 / C8 pdf)
            first = Path(self._files[0])
            suffix = "_slideshow" if out_kind == MediaKind.VIDEO else ""
            dst = self._dest_for(first, out_ext, suffix)
            jobs = [([str(Path(f)) for f in self._files], str(dst), out_ext)]
        else:
            jobs = [
                (str(Path(f)), str(self._dest_for(Path(f), out_ext)), out_ext)
                for f in self._files
            ]

        self._last_output_dir = os.path.dirname(jobs[0][1])
        self._can_open = False
        self.canOpenOutputChanged.emit()
        self._set_progress(0.0)
        self._set_file_progress(0.0)
        self._set_busy(True)

        self._thread = QThread()
        self._worker = ConversionWorker(jobs, opt, tools, soffice)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._set_progress)
        self._worker.fileProgress.connect(self._set_file_progress)
        self._worker.status.connect(self._set_status)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    @Slot()
    def cancel(self):
        if self._worker:
            self._worker.cancel()

    # ---------- helpers ----------
    def _dest_for(self, src: Path, out_ext: str, stem_suffix: str = "") -> Path:
        """출력 경로 결정. 저장 폴더가 지정돼 있으면 그곳에, 아니면 입력과 같은 폴더."""
        base = Path(self._output_dir) if self._output_dir else src.parent
        dst = base / f"{src.stem}{stem_suffix}.{out_ext}"
        if dst == src:  # 입력을 덮어쓰지 않도록
            dst = base / f"{src.stem}{stem_suffix}_converted.{out_ext}"
        return dst

    def _on_finished(self, ok: bool, message: str):
        self._set_status(message)
        self._set_busy(False)
        self._can_open = ok and bool(self._last_output_dir)
        self.canOpenOutputChanged.emit()
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None

    @staticmethod
    def _build_options(o, kind=None, in_kind=None):
        def num(key, cast, default=None):
            v = o.get(key)
            if v in (None, "", 0, "0"):
                return default
            try:
                return cast(v)
            except (ValueError, TypeError):
                return default

        if kind == MediaKind.IMAGE:
            # 영상 → 이미지(C5): gif/webp 애니메이션 또는 프레임 추출
            if in_kind == MediaKind.VIDEO:
                return VideoToImageOptions(
                    fps=num("v2iFps", int),
                    resolution=(o.get("v2iResolution") or None),
                    trim_start=num("trimStart", float),
                    trim_end=num("trimEnd", float),
                )
            # 이미지 → 이미지(C4, Pillow)
            return ImageOptions(
                quality=num("imageQuality", int),
                resolution=(o.get("imageResolution") or None),
            )

        if kind == MediaKind.VIDEO:
            # 이미지 시퀀스 → 영상(C6)
            if in_kind == MediaKind.IMAGE:
                return VideoSequenceOptions(
                    seconds_per_image=num("seqSeconds", float, 1.0) or 1.0,
                    resolution=(o.get("seqResolution") or None),
                    fps=num("seqFps", int, 30) or 30,
                )
            # 영상 → 영상(C1)
            return VideoOptions(
                crf=num("videoQuality", int),
                resolution=(o.get("videoResolution") or None),
                fps=num("videoFps", int),
                audio_bitrate=(o.get("bitrate") or None),
                trim_start=num("trimStart", float),
                trim_end=num("trimEnd", float),
            )

        return AudioOptions(
            bitrate=(o.get("bitrate") or None),
            sample_rate=num("sampleRate", int),
            channels=num("channels", int),
            volume_db=float(o.get("volumeDb") or 0.0),
            normalize=bool(o.get("normalize")),
            trim_start=num("trimStart", float),
            trim_end=num("trimEnd", float),
        )
