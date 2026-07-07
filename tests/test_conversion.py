"""③ 통합 테스트 — 실제 ffmpeg로 변환 (마커: ffmpeg, 일부 gui).

sample_mp4 → mp3 변환을 실제로 실행하고 출력 스트림을 ffprobe로 검증한다.
ffmpeg 미설치 시 자동 skip.
"""
import subprocess

import pytest

from core.media import AudioOptions, build_audio_command, segment_duration


@pytest.mark.ffmpeg
def test_direct_conversion_mp3(tools, sample_mp4, tmp_path, probe):
    out = tmp_path / "o.mp3"
    opt = AudioOptions(sample_rate=44100, channels=2)
    seg = segment_duration(3.0, opt)
    cmd = build_audio_command(tools.ffmpeg, str(sample_mp4), str(out), "mp3", opt, seg)
    subprocess.run(cmd, check=True, capture_output=True)

    assert out.exists() and out.stat().st_size > 0
    info = probe(tools.ffprobe, out)
    assert info.get("codec_name") == "mp3"
    assert info.get("sample_rate") == "44100"
    assert info.get("channels") == "2"


@pytest.mark.ffmpeg
def test_trim_conversion_duration(tools, sample_mp4, tmp_path, probe):
    out = tmp_path / "t.mp3"
    opt = AudioOptions(trim_start=1, trim_end=2)          # 1초 구간
    seg = segment_duration(3.0, opt)
    cmd = build_audio_command(tools.ffmpeg, str(sample_mp4), str(out), "mp3", opt, seg)
    subprocess.run(cmd, check=True, capture_output=True)

    info = probe(tools.ffprobe, out)
    assert 0.8 < float(info["duration"]) < 1.3           # ≈ 1초


@pytest.mark.ffmpeg
def test_convert_to_wav_lossless(tools, sample_mp4, tmp_path, probe):
    out = tmp_path / "o.wav"
    cmd = build_audio_command(
        tools.ffmpeg, str(sample_mp4), str(out), "wav", AudioOptions(), 3.0
    )
    subprocess.run(cmd, check=True, capture_output=True)
    assert out.exists()
    assert probe(tools.ffprobe, out).get("codec_name") == "pcm_s16le"


@pytest.mark.ffmpeg
@pytest.mark.gui
def test_worker_pipeline_single(tools, sample_mp4, tmp_path, run_worker):
    from gui.worker import ConversionWorker

    out = tmp_path / "w.mp3"
    worker = ConversionWorker([(str(sample_mp4), str(out), "mp3")], AudioOptions(), tools)
    progresses = []
    worker.progress.connect(progresses.append)

    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert out.exists()
    assert progresses                                    # 진행률 신호 방출 확인


@pytest.mark.ffmpeg
@pytest.mark.gui
def test_worker_pipeline_multi(tools, sample_mp4, tmp_path, run_worker):
    from gui.worker import ConversionWorker

    jobs = [(str(sample_mp4), str(tmp_path / f"{i}.mp3"), "mp3") for i in range(2)]
    worker = ConversionWorker(jobs, AudioOptions(bitrate="128k"), tools)

    res = run_worker(worker)
    assert res.get("ok") is True, res
    for i in range(2):
        assert (tmp_path / f"{i}.mp3").exists()
