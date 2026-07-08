"""① 단위 테스트 — 변환 실패 메시지 한글화 (core/errors.py)."""
from core.errors import friendly_ffmpeg_error, friendly_image_error


def test_ffmpeg_no_stream():
    msg = friendly_ffmpeg_error("Output file #0 does not contain any stream", "a.mp4")
    assert "a.mp4" in msg and "스트림" in msg


def test_ffmpeg_permission():
    assert "권한" in friendly_ffmpeg_error("Permission denied", "a.mp3")


def test_ffmpeg_corrupt():
    assert "손상" in friendly_ffmpeg_error("Invalid data found when processing input", "x.avi")


def test_ffmpeg_missing_file():
    assert "찾을 수 없" in friendly_ffmpeg_error("No such file or directory", "x.mp4")


def test_ffmpeg_encoder():
    assert "코덱" in friendly_ffmpeg_error("Unknown encoder 'libfoo'", "x.mp4")


def test_ffmpeg_odd_resolution():
    assert "짝수" in friendly_ffmpeg_error("width not divisible by 2", "x.mp4")


def test_ffmpeg_generic():
    msg = friendly_ffmpeg_error("something weird", "x.mp4")
    assert "x.mp4" in msg and "실패" in msg


def test_image_unidentified():
    class UnidentifiedImageError(Exception):
        pass
    msg = friendly_image_error(UnidentifiedImageError("cannot identify image file"), "a.png")
    assert "손상" in msg or "지원하지" in msg


def test_image_generic():
    assert "이미지" in friendly_image_error(ValueError("nope"), "a.png")
