"""① 단위 테스트 — 크기 포맷 및 출력 크기 추정 (core/estimate.py)."""
import pytest

from core.estimate import estimate_output_bytes, format_size


@pytest.mark.parametrize(
    "n,expected",
    [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
        (None, ""),
        (-5, ""),
    ],
)
def test_format_size(n, expected):
    assert format_size(n) == expected


def test_estimate_mp3_bitrate():
    # 192kbps * 60s / 8 = 1,440,000 bytes
    assert estimate_output_bytes("mp3", {"bitrate": "192k"}, [60.0]) == 1_440_000


def test_estimate_mp3_default_bitrate():
    # 비트레이트 미지정 → 기본 192k
    assert estimate_output_bytes("mp3", {}, [60.0]) == 1_440_000


def test_estimate_sums_durations():
    got = estimate_output_bytes("mp3", {"bitrate": "128k"}, [30.0, 30.0])
    assert got == int(128 * 1000 / 8 * 60)


def test_estimate_wav_pcm():
    # 44100 * 2ch * 2byte * 10s
    assert estimate_output_bytes("wav", {}, [10.0]) == 44100 * 2 * 2 * 10


def test_estimate_flac_compressed():
    assert estimate_output_bytes("flac", {}, [10.0]) == int(44100 * 2 * 2 * 10 * 0.6)


def test_estimate_none_for_video_image():
    assert estimate_output_bytes("mp4", {"bitrate": "192k"}, [60.0]) is None
    assert estimate_output_bytes("png", {}, [60.0]) is None
    assert estimate_output_bytes("gif", {}, [60.0]) is None


def test_estimate_none_when_duration_unknown():
    assert estimate_output_bytes("mp3", {"bitrate": "192k"}, [None]) is None
    assert estimate_output_bytes("mp3", {"bitrate": "192k"}, []) is None
