"""② GUI 스모크 테스트 (마커: gui) — QML 로드 + Backend 로직.

offscreen 플랫폼으로 화면 없이 실행. PySide6 미설치 시 자동 skip.
"""
from pathlib import Path

import pytest

QML = Path(__file__).resolve().parent.parent / "gui" / "qml" / "main.qml"


@pytest.mark.gui
def test_qml_loads(qapp):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    from gui.backend import Backend

    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("appVersion", "test")
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), "QML 로드 실패"


@pytest.mark.gui
def test_backend_filters_unsupported(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/movie.mp4", "file:///C:/a/note.txt"])
    assert b.files == ["movie.mp4"]                       # 지원 확장자만 남음


@pytest.mark.gui
def test_backend_output_formats(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/movie.mp4"])
    assert "mp3" in b.outputFormats


@pytest.mark.gui
def test_backend_clear(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/movie.mp4"])
    b.clearFiles()
    assert b.files == []
    assert b.outputFormats == []


@pytest.mark.gui
def test_options_conversion(qapp):
    from gui.backend import Backend

    opt = Backend._build_options({
        "bitrate": "320k", "sampleRate": 48000, "channels": 1,
        "volumeDb": 3, "normalize": True, "trimStart": "10", "trimEnd": "40",
    })
    assert opt.bitrate == "320k"
    assert opt.sample_rate == 48000
    assert opt.channels == 1
    assert opt.normalize is True
    assert opt.trim_start == 10.0 and opt.trim_end == 40.0


@pytest.mark.gui
def test_options_defaults_empty(qapp):
    from gui.backend import Backend

    opt = Backend._build_options({})
    assert opt.sample_rate is None                        # 원본 유지
    assert opt.channels is None
    assert opt.trim_start is None
