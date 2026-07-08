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
    from gui.update_checker import UpdateChecker

    engine = QQmlApplicationEngine()
    backend = Backend()
    updater = UpdateChecker("0.0.1")
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("updater", updater)
    engine.rootContext().setContextProperty("appVersion", "test")
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), "QML 로드 실패"


@pytest.mark.gui
def test_update_checker_available(qapp):
    from gui.update_checker import UpdateChecker

    checker = UpdateChecker("0.0.1")
    # 스레드/네트워크 없이 결과 핸들러를 직접 호출해 상태 전이만 검증
    checker._on_check_done({
        "tag": "v0.0.2",
        "body": "<!--CHANGES-->\n- 새 기능\n<!--/CHANGES-->",
    })
    assert checker.available is True
    assert checker.latestVersion == "v0.0.2"
    assert "새 기능" in checker.changes


@pytest.mark.gui
def test_update_checker_none_keeps_hidden(qapp):
    from gui.update_checker import UpdateChecker

    checker = UpdateChecker("0.0.1")
    checker._on_check_done(None)          # 최신이 아님
    assert checker.available is False


@pytest.mark.gui
def test_update_checker_dismiss(qapp):
    from gui.update_checker import UpdateChecker

    checker = UpdateChecker("0.0.1")
    checker._on_check_done({"tag": "v0.0.2", "body": ""})
    checker.dismiss()
    assert checker.available is False


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
    assert "mp3" in b.outputFormats      # 음원 출력(C2)
    assert "mkv" in b.outputFormats      # 영상 출력(C1)


@pytest.mark.gui
def test_backend_output_kind(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/movie.mp4"])
    assert b.outputKind == "video"       # 기본 출력이 영상(mkv)
    b.setOutputFormat("mp3")
    assert b.outputKind == "audio"
    b.setOutputFormat("webm")
    assert b.outputKind == "video"


@pytest.mark.gui
def test_backend_build_video_options(qapp):
    from core.registry import MediaKind
    from gui.backend import Backend

    opt = Backend._build_options(
        {"videoResolution": "720", "videoFps": 30, "videoQuality": 23,
         "bitrate": "192k", "trimStart": "5", "trimEnd": "10"},
        MediaKind.VIDEO,
    )
    assert opt.resolution == "720"
    assert opt.fps == 30
    assert opt.crf == 23
    assert opt.audio_bitrate == "192k"
    assert opt.trim_start == 5.0


@pytest.mark.gui
def test_backend_image_kind_and_options(qapp):
    from core.registry import MediaKind
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/pic.png"])
    assert b.outputKind == "image"          # 이미지 입력 → 이미지 출력
    assert "jpg" in b.outputFormats
    assert "mp3" not in b.outputFormats

    opt = Backend._build_options(
        {"imageResolution": "720", "imageQuality": 85}, MediaKind.IMAGE,
    )
    assert opt.resolution == "720"
    assert opt.quality == 85


@pytest.mark.gui
def test_backend_video_to_image(qapp):
    from core.registry import MediaKind
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/v/clip.mp4"])
    assert b.inputKind == "video"
    assert "gif" in b.outputFormats            # 영상→이미지 출력 제공
    b.setOutputFormat("gif")
    assert b.outputKind == "image"

    # 영상 입력 + 이미지 출력 → VideoToImageOptions
    opt = Backend._build_options(
        {"v2iFps": 8, "v2iResolution": "480", "trimStart": "0", "trimEnd": "3"},
        MediaKind.IMAGE, MediaKind.VIDEO,
    )
    assert type(opt).__name__ == "VideoToImageOptions"
    assert opt.fps == 8
    assert opt.resolution == "480"
    assert opt.trim_end == 3.0


@pytest.mark.gui
def test_backend_image_sequence_to_video(qapp):
    from core.registry import MediaKind
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/p/a.png", "file:///C:/p/b.png"])
    assert b.inputKind == "image"
    assert "mp4" in b.outputFormats            # 이미지 시퀀스→영상(C6)
    b.setOutputFormat("mp4")
    assert b.outputKind == "video"

    opt = Backend._build_options(
        {"seqSeconds": 2, "seqResolution": "1920x1080", "seqFps": 24},
        MediaKind.VIDEO, MediaKind.IMAGE,
    )
    assert type(opt).__name__ == "VideoSequenceOptions"
    assert opt.seconds_per_image == 2
    assert opt.resolution == "1920x1080"
    assert opt.fps == 24


@pytest.mark.gui
def test_backend_clear(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/movie.mp4"])
    b.clearFiles()
    assert b.files == []
    assert b.outputFormats == []


@pytest.mark.gui
def test_backend_reorder(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/p/a.png", "file:///C:/p/b.png", "file:///C:/p/c.png"])
    assert b.files == ["a.png", "b.png", "c.png"]

    b.moveDown(0)
    assert b.files == ["b.png", "a.png", "c.png"]
    b.moveUp(2)
    assert b.files == ["b.png", "c.png", "a.png"]

    # 경계는 무시(no-op)
    b.moveUp(0)
    b.moveDown(2)
    assert b.files == ["b.png", "c.png", "a.png"]


@pytest.mark.gui
def test_backend_remove(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/p/a.png", "file:///C:/p/b.png"])
    b.removeAt(0)
    assert b.files == ["b.png"]
    b.removeAt(0)
    assert b.files == []


@pytest.mark.gui
def test_reorder_preserves_output_selection(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/v/a.mp4", "file:///C:/v/b.mp4"])
    b.setOutputFormat("mp3")
    assert b.outputKind == "audio"

    b.moveDown(0)                       # 순서만 변경
    assert b.outputKind == "audio"      # 선택 유지(초기화 안 됨)
    assert "mp3" in b.outputFormats


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
