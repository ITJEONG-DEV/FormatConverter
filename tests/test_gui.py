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
    b.addUrls(["file:///C:/a/movie.mp4", "file:///C:/a/note.zzz"])
    assert b.files == ["movie.mp4"]                       # 지원 확장자만 남음


@pytest.mark.gui
def test_backend_output_formats(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/movie.mp4"])
    # 기본 종류는 영상 → 영상 포맷만 노출(목록이 짧아짐)
    assert "mkv" in b.outputFormats
    assert "mp3" not in b.outputFormats
    # 음원 종류로 전환하면 음원 포맷
    b.setOutputCategory("audio")
    assert "mp3" in b.outputFormats


@pytest.mark.gui
def test_backend_output_category(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/v/a.mp4"])
    assert [c["value"] for c in b.outputCategories] == ["video", "audio", "image"]
    assert b.selectedCategory == "video"
    assert "mkv" in b.outputFormats and "mp3" not in b.outputFormats

    b.setOutputCategory("audio")
    assert b.selectedCategory == "audio"
    assert b.outputKind == "audio"
    assert "mp3" in b.outputFormats and "mkv" not in b.outputFormats

    b.setOutputCategory("image")
    assert "gif" in b.outputFormats
    assert b.outputKind == "image"


@pytest.mark.gui
def test_audio_input_single_category(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/a/song.wav"])
    # 음원 입력은 음원 출력 한 종류뿐 → 종류 선택 UI 숨김 대상
    assert [c["value"] for c in b.outputCategories] == ["audio"]


@pytest.mark.gui
def test_backend_document_input(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/d/report.docx"])
    assert b.inputKind == "document"
    # docx는 문서→문서만 (pdf 렌더는 pdf 입력만 가능)
    assert [c["value"] for c in b.outputCategories] == ["document"]
    assert "pdf" in b.outputFormats
    b.setOutputFormat("pdf")
    assert b.outputKind == "document"


@pytest.mark.gui
def test_backend_image_to_pdf(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/p/a.png"])
    assert "document" in [c["value"] for c in b.outputCategories]  # 이미지→pdf
    b.setOutputCategory("document")
    assert b.outputFormats == ["pdf"]
    assert b.outputKind == "document"


@pytest.mark.gui
def test_backend_pdf_to_image(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/d/doc.pdf"])
    assert b.inputKind == "document"
    assert [c["value"] for c in b.outputCategories] == ["document", "image"]
    b.setOutputCategory("image")
    assert "png" in b.outputFormats and "jpg" in b.outputFormats
    b.setOutputFormat("png")
    assert b.outputKind == "image"


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
    b.setOutputCategory("image")               # 영상→이미지 종류 선택
    assert "gif" in b.outputFormats
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
    assert b.selectedCategory == "image"       # 기본은 이미지→이미지
    b.setOutputCategory("video")               # 이미지 시퀀스→영상(C6)
    assert "mp4" in b.outputFormats
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
def test_backend_file_infos_size(qapp, tmp_path):
    from gui.backend import Backend

    f1 = tmp_path / "a.mp3"
    f1.write_bytes(b"x" * 2048)
    b = Backend()
    b._files = [str(f1)]                 # 프로브 스레드 없이 프로퍼티만 검증
    infos = b.fileInfos
    assert infos[0]["name"] == "a.mp3"
    assert infos[0]["size"] == "2.0 KB"


@pytest.mark.gui
def test_backend_estimate_audio(qapp):
    from gui.backend import Backend

    b = Backend()
    b._files = ["/x/a.mp3"]
    b._output_format = "mp3"
    b._durations = {"/x/a.mp3": 60.0}
    b._estimate_options = {"bitrate": "192k"}
    b._recompute_estimate()
    assert "1.4 MB" in b.estimatedSize   # 192k*60/8 = 1,440,000 B

    # 비오디오 출력은 추정 안 함 → 빈 문자열
    b._output_format = "mkv"
    b._recompute_estimate()
    assert b.estimatedSize == ""


@pytest.mark.gui
def test_backend_update_estimate_reacts_to_bitrate(qapp):
    from gui.backend import Backend

    b = Backend()
    b._files = ["/x/a.mp3"]
    b._output_format = "mp3"
    b._durations = {"/x/a.mp3": 30.0}
    b.updateEstimate({"bitrate": "320k"})   # 320k*30/8 = 1,200,000 B ≈ 1.1 MB
    assert "1.1 MB" in b.estimatedSize


@pytest.mark.gui
def test_backend_output_dir(qapp):
    from PySide6.QtCore import QUrl
    from gui.backend import Backend

    b = Backend()
    assert b.outputDir == ""                     # 기본: 입력과 같은 폴더
    b.setOutputDir(QUrl.fromLocalFile("C:/out"))
    assert b.outputDir == "C:/out"
    b.clearOutputDir()
    assert b.outputDir == ""


@pytest.mark.gui
def test_dest_for_uses_output_dir(qapp):
    from pathlib import Path
    from gui.backend import Backend

    b = Backend()
    src = Path("C:/videos/clip.mp4")
    # 저장 폴더 미지정 → 입력과 같은 폴더
    assert b._dest_for(src, "mp3") == Path("C:/videos/clip.mp3")
    # 저장 폴더 지정 → 그 폴더에
    b._output_dir = "D:/out"
    assert b._dest_for(src, "mp3") == Path("D:/out/clip.mp3")
    # 같은 폴더+같은 확장자면 덮어쓰기 방지
    b._output_dir = ""
    assert b._dest_for(src, "mp4") == Path("C:/videos/clip_converted.mp4")


@pytest.mark.gui
def test_can_open_output_after_finish(qapp):
    from gui.backend import Backend

    b = Backend()
    b._last_output_dir = "C:/out"
    b._on_finished(True, "완료")
    assert b.canOpenOutput is True
    b._on_finished(False, "오류")
    assert b.canOpenOutput is False


@pytest.mark.gui
def test_reorder_preserves_output_selection(qapp):
    from gui.backend import Backend

    b = Backend()
    b.addUrls(["file:///C:/v/a.mp4", "file:///C:/v/b.mp4"])
    b.setOutputCategory("audio")
    b.setOutputFormat("mp3")
    assert b.outputKind == "audio"

    b.moveDown(0)                       # 순서만 변경
    assert b.selectedCategory == "audio"  # 종류 유지
    assert b.outputKind == "audio"        # 포맷 유지(초기화 안 됨)
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
