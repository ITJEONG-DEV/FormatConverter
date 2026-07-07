"""QML <-> Python 브리지. 파일 목록, 옵션, 변환 실행을 담당한다."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    Property, QObject, QThread, QUrl, Signal, Slot,
)

from core.ffmpeg_tools import FFmpegNotFound, find_tools
from core.media import AudioOptions
from core.registry import is_supported_input, output_formats_for
from gui.worker import ConversionWorker


class Backend(QObject):
    filesChanged = Signal()
    outputFormatsChanged = Signal()
    progressChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()

    def __init__(self):
        super().__init__()
        self._files: list[str] = []
        self._output_formats: list[str] = []
        self._output_format: str = ""
        self._progress: float = 0.0
        self._status: str = "파일을 끌어다 놓으세요."
        self._busy: bool = False
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None

    # ---------- Properties ----------
    @Property(list, notify=filesChanged)
    def files(self):
        return [Path(f).name for f in self._files]

    @Property(list, notify=outputFormatsChanged)
    def outputFormats(self):
        return self._output_formats

    @Property(float, notify=progressChanged)
    def progress(self):
        return self._progress

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

    def _set_busy(self, value: bool):
        self._busy = value
        self.busyChanged.emit()

    def _refresh_output_formats(self):
        if not self._files:
            self._output_formats = []
        else:
            first_ext = Path(self._files[0]).suffix.lstrip(".")
            self._output_formats = output_formats_for(first_ext)
        if self._output_formats:
            self._output_format = self._output_formats[0]
        self.outputFormatsChanged.emit()

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
            self._set_status(f"{len(self._files)}개 파일 준비됨.")
        elif not self._files:
            self._set_status("지원하지 않는 파일이거나 추가된 파일이 없습니다.")

    @Slot()
    def clearFiles(self):
        self._files.clear()
        self.filesChanged.emit()
        self._refresh_output_formats()
        self._set_progress(0.0)
        self._set_status("파일을 끌어다 놓으세요.")

    @Slot(str)
    def setOutputFormat(self, fmt: str):
        self._output_format = fmt

    @Slot("QVariantMap")
    def start(self, options):
        if self._busy:
            return
        if not self._files:
            self._set_status("변환할 파일이 없습니다.")
            return
        try:
            tools = find_tools()
        except FFmpegNotFound as exc:
            self._set_status(str(exc))
            return

        out_ext = self._output_format or (
            self._output_formats[0] if self._output_formats else "mp3"
        )
        opt = self._build_options(options)

        jobs = []
        for f in self._files:
            src = Path(f)
            dst = src.with_name(f"{src.stem}.{out_ext}")
            if dst == src:
                dst = src.with_name(f"{src.stem}_converted.{out_ext}")
            jobs.append((str(src), str(dst), out_ext))

        self._set_progress(0.0)
        self._set_busy(True)

        self._thread = QThread()
        self._worker = ConversionWorker(jobs, opt, tools)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._set_progress)
        self._worker.status.connect(self._set_status)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    @Slot()
    def cancel(self):
        if self._worker:
            self._worker.cancel()

    # ---------- helpers ----------
    def _on_finished(self, ok: bool, message: str):
        self._set_status(message)
        self._set_busy(False)
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None

    @staticmethod
    def _build_options(o) -> AudioOptions:
        def num(key, cast, default=None):
            v = o.get(key)
            if v in (None, "", 0, "0"):
                return default
            try:
                return cast(v)
            except (ValueError, TypeError):
                return default

        return AudioOptions(
            bitrate=(o.get("bitrate") or None),
            sample_rate=num("sampleRate", int),
            channels=num("channels", int),
            volume_db=float(o.get("volumeDb") or 0.0),
            normalize=bool(o.get("normalize")),
            trim_start=num("trimStart", float),
            trim_end=num("trimEnd", float),
        )
