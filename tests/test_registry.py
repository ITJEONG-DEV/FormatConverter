"""① 단위 테스트 — 포맷/카테고리 라우팅 (core/registry.py)."""
from core.registry import MediaKind, is_supported_input, kind_of, output_formats_for


def test_kind_of():
    assert kind_of("mp4") == MediaKind.VIDEO
    assert kind_of("MP3") == MediaKind.AUDIO      # 대문자 정규화
    assert kind_of(".png") == MediaKind.IMAGE     # 선행 점 허용
    assert kind_of("nope") is None


def test_is_supported_input():
    assert is_supported_input("mp4")              # 영상 → 음원 (구현됨)
    assert is_supported_input("wav")              # 음원 → 음원 (구현됨)
    assert not is_supported_input("png")          # 이미지 출력 미구현
    assert not is_supported_input("txt")          # 미지원 확장자


def test_output_formats_for_video():
    outs = output_formats_for("mp4")
    assert "mp3" in outs and "aac" in outs and "wav" in outs
    assert outs == sorted(outs)                   # 정렬 보장


def test_output_formats_for_audio():
    assert "mp3" in output_formats_for("wav")


def test_output_formats_for_unsupported():
    assert output_formats_for("png") == []
    assert output_formats_for("xyz") == []
