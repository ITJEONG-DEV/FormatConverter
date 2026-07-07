"""FormatConverter 진입점."""
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from gui.backend import Backend
from gui.update_checker import UpdateChecker

try:
    from version import __version__
except ImportError:
    __version__ = "0.0.0"


def _base_dir() -> Path:
    """개발/번들(PyInstaller) 모두에서 리소스 루트를 반환."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("FormatConverter")
    app.setOrganizationName("FormatConverter")
    app.setApplicationVersion(__version__)

    engine = QQmlApplicationEngine()
    backend = Backend()
    updater = UpdateChecker(__version__)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("updater", updater)
    engine.rootContext().setContextProperty("appVersion", __version__)

    qml_path = _base_dir() / "gui" / "qml" / "main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        return -1

    updater.start()  # 기동 후 백그라운드로 최신 버전 확인(dev는 skip)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
