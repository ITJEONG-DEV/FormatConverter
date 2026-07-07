"""① 단위 + ③ 통합 — ffmpeg 탐색 및 미디어 정보 조회 (core/ffmpeg_tools.py)."""
import pytest

from core import ffmpeg_tools


def test_find_tools_missing(monkeypatch):
    """후보 폴더·PATH 어디에도 없으면 FFmpegNotFound."""
    monkeypatch.setattr(ffmpeg_tools, "_candidate_dirs", lambda: [])
    monkeypatch.setattr(ffmpeg_tools.shutil, "which", lambda name: None)
    with pytest.raises(ffmpeg_tools.FFmpegNotFound):
        ffmpeg_tools.find_tools()


def test_find_tools_from_path(monkeypatch):
    """ffmpeg만 PATH에 있고 ffprobe 없으면 ffprobe는 빈 문자열."""
    monkeypatch.setattr(ffmpeg_tools, "_candidate_dirs", lambda: [])
    monkeypatch.setattr(
        ffmpeg_tools.shutil, "which",
        lambda name: "C:/x/ffmpeg.exe" if name == "ffmpeg" else None,
    )
    t = ffmpeg_tools.find_tools()
    assert t.ffmpeg.endswith("ffmpeg.exe")
    assert t.ffprobe == ""


@pytest.mark.ffmpeg
def test_probe_duration(tools, sample_mp4):
    d = ffmpeg_tools.probe_duration(tools.ffprobe, str(sample_mp4))
    assert d is not None
    assert 2.5 < d < 3.5                          # 3초 샘플


@pytest.mark.ffmpeg
def test_probe_duration_bad_path(tools):
    assert ffmpeg_tools.probe_duration(tools.ffprobe, "no_such_file.mp4") is None
