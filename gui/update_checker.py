"""자동 업데이트 QML 브리지.

- 실행 직후 백그라운드 스레드로 GitHub 최신 릴리스를 확인(패키지 빌드만, dev는 기본 skip).
- 새 버전이 있으면 QML 다이얼로그를 띄우고, [업데이트] 시 다운로드→도우미 실행→앱 종료.
"""
from __future__ import annotations

import os

from PySide6.QtCore import (
    Property, QCoreApplication, QObject, QThread, QTimer, Signal, Slot,
)

from core import updater as up


class _CheckWorker(QObject):
    done = Signal(object)     # latest dict 또는 None
    failed = Signal(str)

    def __init__(self, current: str):
        super().__init__()
        self._current = current

    @Slot()
    def run(self):
        try:
            self.done.emit(up.check_update(self._current))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _ApplyWorker(QObject):
    progress = Signal(float)
    done = Signal()
    failed = Signal(str)

    def __init__(self, latest: dict, kind: str):
        super().__init__()
        self._latest = latest
        self._kind = kind

    @Slot()
    def run(self):
        try:
            up.download_and_apply(self._latest, self._kind, self.progress.emit)
            self.done.emit()
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class UpdateChecker(QObject):
    availableChanged = Signal()
    latestVersionChanged = Signal()
    changesChanged = Signal()
    progressChanged = Signal()
    busyChanged = Signal()
    messageChanged = Signal()

    def __init__(self, current_version: str):
        super().__init__()
        self._current = current_version
        self._latest: dict | None = None
        self._available = False
        self._latest_version = ""
        self._changes = ""
        self._progress = 0.0
        self._busy = False
        self._message = ""
        self._thread: QThread | None = None
        self._worker: QObject | None = None

    # ---------- Properties ----------
    @Property(bool, notify=availableChanged)
    def available(self):
        return self._available

    @Property(str, notify=latestVersionChanged)
    def latestVersion(self):
        return self._latest_version

    @Property(str, notify=changesChanged)
    def changes(self):
        return self._changes

    @Property(float, notify=progressChanged)
    def progress(self):
        return self._progress

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=messageChanged)
    def message(self):
        return self._message

    # ---------- setters ----------
    def _set_available(self, v):
        self._available = v
        self.availableChanged.emit()

    def _set_progress(self, v):
        self._progress = v
        self.progressChanged.emit()

    def _set_busy(self, v):
        self._busy = v
        self.busyChanged.emit()

    def _set_message(self, v):
        self._message = v
        self.messageChanged.emit()

    # ---------- 시작 ----------
    def start(self, delay_ms: int = 1500):
        """앱 기동 후 자동 확인 예약. dev 빌드는 기본 skip(환경변수로 강제 가능)."""
        force = os.environ.get("FORMATCONVERTER_FORCE_UPDATE") == "1"
        if up.build_kind() == "dev" and not force:
            return
        QTimer.singleShot(delay_ms, self.check)

    @Slot()
    def check(self):
        if self._busy or self._thread is not None:
            return
        self._start_worker(_CheckWorker(self._current), self._on_check_done, self._on_check_failed)

    def _on_check_done(self, latest):
        self._teardown_thread()
        if latest:
            self._latest = latest
            self._latest_version = latest.get("tag", "")
            self.latestVersionChanged.emit()
            self._changes = up.extract_summary(latest.get("body", ""))
            self.changesChanged.emit()
            self._set_available(True)

    def _on_check_failed(self, msg):
        self._teardown_thread()
        # 조용히 무시(네트워크 없음 등) — 상태만 기록
        self._set_message(f"업데이트 확인 실패: {msg}")

    @Slot()
    def apply(self):
        if self._busy or not self._latest:
            return
        self._set_busy(True)
        self._set_message("업데이트 다운로드 중…")
        worker = _ApplyWorker(self._latest, up.build_kind())
        worker.progress.connect(self._set_progress)
        self._start_worker(worker, self._on_apply_done, self._on_apply_failed)

    def _on_apply_done(self):
        self._teardown_thread()
        self._set_message("재시작하여 업데이트를 적용합니다…")
        # 도우미가 프로세스 종료를 기다리므로 앱을 종료한다.
        QCoreApplication.instance().quit()

    def _on_apply_failed(self, msg):
        self._teardown_thread()
        self._set_busy(False)
        self._set_message(f"업데이트 실패: {msg}")

    @Slot()
    def dismiss(self):
        self._set_available(False)

    # ---------- 스레드 관리 ----------
    def _start_worker(self, worker, on_done, on_failed):
        self._thread = QThread()
        self._worker = worker
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.done.connect(on_done)
        worker.failed.connect(on_failed)
        self._thread.start()

    def _teardown_thread(self):
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        self._thread = None
        self._worker = None
