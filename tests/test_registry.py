"""① 단위 테스트 — 포맷/카테고리 라우팅 (core/registry.py)."""
from core.registry import (
    MediaKind, is_supported_input, kind_of, output_categories_for, output_formats_for,
)


def test_output_categories():
    assert output_categories_for("mp4") == [
        MediaKind.VIDEO, MediaKind.AUDIO, MediaKind.IMAGE,
    ]
    assert output_categories_for("wav") == [MediaKind.AUDIO]
    assert output_categories_for("png") == [MediaKind.IMAGE, MediaKind.VIDEO]
    assert output_categories_for("docx") == [MediaKind.DOCUMENT]
    assert output_categories_for("zzz") == []


def test_output_formats_by_category():
    auds = output_formats_for("mp4", MediaKind.AUDIO)
    assert "mp3" in auds and "mkv" not in auds and "gif" not in auds
    imgs = output_formats_for("mp4", MediaKind.IMAGE)
    assert "gif" in imgs and "mp3" not in imgs and "mkv" not in imgs


def test_kind_of():
    assert kind_of("mp4") == MediaKind.VIDEO
    assert kind_of("MP3") == MediaKind.AUDIO      # 대문자 정규화
    assert kind_of(".png") == MediaKind.IMAGE     # 선행 점 허용
    assert kind_of("nope") is None


def test_is_supported_input():
    assert is_supported_input("mp4")              # 영상 → 영상/음원 (구현됨)
    assert is_supported_input("wav")              # 음원 → 음원 (구현됨)
    assert is_supported_input("png")              # 이미지 → 이미지 (C4 구현됨)
    assert is_supported_input("docx")             # 문서 → 문서 (C7 구현됨)
    assert not is_supported_input("zzz")          # 미지원 확장자


def test_output_formats_for_image():
    outs = output_formats_for("png")
    assert "jpg" in outs and "webp" in outs and "bmp" in outs  # 이미지→이미지(C4)
    assert "mp4" in outs                          # 이미지 시퀀스→영상(C6)
    assert "mp3" not in outs                       # 이미지 → 음원 없음
    assert outs[0] == "jpg"                       # 같은 종류(이미지) 먼저, 동일 확장자(png)는 뒤로
    assert outs.index("jpg") < outs.index("mp4")  # 이미지 출력이 영상 출력보다 앞


def test_output_formats_for_video():
    outs = output_formats_for("mp4")
    # 영상 출력(C1) + 음원 출력(C2) + 이미지 출력(C5) 모두 제공
    assert "mkv" in outs and "webm" in outs       # 영상→영상
    assert "mp3" in outs and "aac" in outs        # 영상→음원
    assert "gif" in outs and "png" in outs        # 영상→이미지
    # 영상 입력이므로 영상 포맷이 먼저, 동일 확장자(mp4)는 기본값이 아님
    assert outs[0] == "mkv"
    assert outs.index("mkv") < outs.index("mp3")  # 같은 종류(영상) 먼저


def test_output_formats_for_audio():
    outs = output_formats_for("wav")
    assert "mp3" in outs
    assert outs[0] == "mp3"                        # 흔한 포맷 우선, 동일 확장자(wav)는 뒤로
    assert "mkv" not in outs                       # 음원 입력 → 영상 출력 없음


def test_output_formats_for_unsupported():
    assert output_formats_for("zzz") == []
    assert output_formats_for("xyz") == []
