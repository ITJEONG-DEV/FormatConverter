"""① 단위 테스트 — FFmpeg 명령 생성 (core/media.py).

subprocess 를 실제로 실행하지 않고, 만들어진 인자 리스트만 검증한다(빠름).
"""
import pytest

from core.media import AudioOptions, build_audio_command, segment_duration


def build(ext="mp3", seg=None, **kw):
    return build_audio_command("ffmpeg", "in.mp4", f"out.{ext}", ext, AudioOptions(**kw), seg)


def test_default_mp3_has_codec_and_bitrate():
    c = build()
    assert "-vn" in c                                     # 영상 트랙 제거
    assert c[c.index("-c:a") + 1] == "libmp3lame"
    assert c[c.index("-b:a") + 1] == "192k"


@pytest.mark.parametrize(
    "ext,codec",
    [
        ("mp3", "libmp3lame"), ("aac", "aac"), ("m4a", "aac"),
        ("ogg", "libvorbis"), ("opus", "libopus"),
        ("wav", "pcm_s16le"), ("flac", "flac"), ("aiff", "pcm_s16be"),
    ],
)
def test_codec_selection(ext, codec):
    assert build(ext=ext)[build(ext=ext).index("-c:a") + 1] == codec


def test_lossless_skips_bitrate():
    c = build(ext="wav", bitrate="192k")
    assert "-b:a" not in c                                # 무손실은 비트레이트 미적용


def test_trim_placed_before_input():
    c = build(trim_start=30, trim_end=90)
    i = c.index("-i")
    assert c.index("-ss") < i and c.index("-to") < i      # 입력 옵션으로 배치
    assert c[c.index("-ss") + 1] == "30"
    assert c[c.index("-to") + 1] == "90"


def test_sample_rate_and_channels():
    c = build(sample_rate=48000, channels=1)
    assert c[c.index("-ar") + 1] == "48000"
    assert c[c.index("-ac") + 1] == "1"


def test_filters_volume_and_normalize():
    c = build(seg=60, volume_db=3, normalize=True)
    af = c[c.index("-af") + 1]
    assert "volume=3" in af
    assert "loudnorm" in af


def test_fade_out_uses_segment_duration():
    c = build(seg=60, fade_out=5)
    af = c[c.index("-af") + 1]
    assert "afade=t=out:st=55" in af                      # 60 - 5 = 55


def test_vbr_overrides_bitrate():
    c = build(vbr_quality=2, bitrate="192k")
    assert "-q:a" in c
    assert "-b:a" not in c


def test_progress_pipe_present():
    assert "-progress" in build()                         # 진행률 파이프


def test_segment_duration():
    assert segment_duration(120, AudioOptions(trim_start=30, trim_end=90)) == 60
    assert segment_duration(120, AudioOptions()) == 120
    assert segment_duration(None, AudioOptions()) is None
