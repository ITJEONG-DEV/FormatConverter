"""FormatConverter 진입점."""
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from gui.backend import Backend


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("FormatConverter")
    app.setOrganizationName("FormatConverter")

    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    qml_path = Path(__file__).resolve().parent / "gui" / "qml" / "main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        return -1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
