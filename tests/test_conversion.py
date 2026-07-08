"""③ 통합 테스트 — 실제 ffmpeg로 변환 (마커: ffmpeg, 일부 gui).

sample_mp4 → mp3 변환을 실제로 실행하고 출력 스트림을 ffprobe로 검증한다.
ffmpeg 미설치 시 자동 skip.
"""
import subprocess

import pytest

from core.media import (
    AudioOptions, VideoOptions, VideoToImageOptions,
    build_audio_command, build_command, segment_duration,
)


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


# ----- C1: 영상 → 영상 -----
def _video_codec(ffprobe, path):
    out = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name", "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


@pytest.mark.ffmpeg
def test_video_conversion_mp4_to_mkv(tools, sample_mp4, tmp_path):
    out = tmp_path / "o.mkv"
    cmd = build_command(tools.ffmpeg, str(sample_mp4), str(out), "mkv", VideoOptions(), 3.0)
    subprocess.run(cmd, check=True, capture_output=True)
    assert out.exists() and out.stat().st_size > 0
    assert _video_codec(tools.ffprobe, out) == "h264"


@pytest.mark.ffmpeg
def test_video_conversion_resize(tools, sample_mp4, tmp_path):
    out = tmp_path / "r.mp4"
    opt = VideoOptions(resolution="120", crf=28)
    cmd = build_command(tools.ffmpeg, str(sample_mp4), str(out), "mp4", opt, 3.0)
    subprocess.run(cmd, check=True, capture_output=True)
    # 세로 해상도가 120으로 축소됐는지 확인
    info = subprocess.run(
        [tools.ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=height", "-of", "default=nk=1:nw=1", str(out)],
        capture_output=True, text=True, check=True,
    )
    assert info.stdout.strip() == "120"


@pytest.mark.ffmpeg
@pytest.mark.gui
def test_worker_video_pipeline(tools, sample_mp4, tmp_path, run_worker):
    from gui.worker import ConversionWorker

    out = tmp_path / "w.mkv"
    worker = ConversionWorker([(str(sample_mp4), str(out), "mkv")], VideoOptions(), tools)
    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert out.exists()


# ----- C5: 영상 → 이미지 -----
@pytest.mark.ffmpeg
def test_video_to_gif(tools, sample_mp4, tmp_path):
    out = tmp_path / "o.gif"
    opt = VideoToImageOptions(fps=8, resolution="120", trim_start=0, trim_end=2)
    seg = segment_duration(3.0, opt)
    cmd = build_command(tools.ffmpeg, str(sample_mp4), str(out), "gif", opt, seg)
    subprocess.run(cmd, check=True, capture_output=True)
    assert out.exists() and out.stat().st_size > 0
    assert _video_codec(tools.ffprobe, out) == "gif"


@pytest.mark.ffmpeg
def test_video_to_png_frame(tools, sample_mp4, tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    out = tmp_path / "f.png"
    cmd = build_command(tools.ffmpeg, str(sample_mp4), str(out), "png",
                        VideoToImageOptions(trim_start=1), None)
    subprocess.run(cmd, check=True, capture_output=True)
    assert out.exists()
    with Image.open(out) as im:
        assert im.format == "PNG"


@pytest.mark.ffmpeg
@pytest.mark.gui
def test_worker_video_to_gif_pipeline(tools, sample_mp4, tmp_path, run_worker):
    from gui.worker import ConversionWorker

    out = tmp_path / "w.gif"
    worker = ConversionWorker(
        [(str(sample_mp4), str(out), "gif")],
        VideoToImageOptions(fps=8, trim_start=0, trim_end=1), tools,
    )
    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert out.exists()


# ----- C6: 이미지 시퀀스 → 영상 -----
@pytest.mark.ffmpeg
def test_image_sequence_to_mp4(tools, tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    from core.media import (
        VideoSequenceOptions, build_image_sequence_command, write_concat_file,
    )

    imgs = []
    for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        p = tmp_path / f"img{i}.png"
        Image.new("RGB", (320, 240), color).save(p)
        imgs.append(str(p))

    opt = VideoSequenceOptions(seconds_per_image=0.5, resolution="640x480", fps=10)
    concat = str(tmp_path / "list.txt")
    write_concat_file(imgs, opt.seconds_per_image, concat)
    out = tmp_path / "slide.mp4"
    cmd = build_image_sequence_command(tools.ffmpeg, concat, str(out), "mp4", opt)
    subprocess.run(cmd, check=True, capture_output=True)

    assert out.exists() and out.stat().st_size > 0
    dims = subprocess.run(
        [tools.ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "default=nw=1:nk=1", str(out)],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    assert dims == ["640", "480"]


@pytest.mark.ffmpeg
@pytest.mark.gui
def test_worker_sequence_pipeline(tools, tmp_path, run_worker):
    pytest.importorskip("PIL")
    from PIL import Image

    from core.media import VideoSequenceOptions
    from gui.worker import ConversionWorker

    imgs = []
    for i, color in enumerate([(10, 20, 30), (40, 50, 60)]):
        p = tmp_path / f"s{i}.png"
        Image.new("RGB", (100, 100), color).save(p)
        imgs.append(str(p))
    out = tmp_path / "seq.mp4"

    # inp가 리스트인 시퀀스 잡
    worker = ConversionWorker(
        [(imgs, str(out), "mp4")],
        VideoSequenceOptions(seconds_per_image=0.5, resolution="320x240", fps=10), tools,
    )
    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert out.exists() and out.stat().st_size > 0


# ----- 실패 메시지 한글화 + 현재 파일 진행률 -----
@pytest.mark.ffmpeg
@pytest.mark.gui
def test_worker_friendly_error(tools, tmp_path, run_worker):
    from core.media import AudioOptions
    from gui.worker import ConversionWorker

    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"this is not a real video file")
    out = tmp_path / "o.mp3"

    worker = ConversionWorker([(str(bad), str(out), "mp3")], AudioOptions(), tools)
    res = run_worker(worker)
    assert res.get("ok") is False
    msg = res.get("msg", "")
    assert "bad.mp4" in msg                     # 어떤 파일인지 안내
    assert "ffmpeg 종료 코드" not in msg        # 기술적 원문이 아님


@pytest.mark.ffmpeg
@pytest.mark.gui
def test_worker_file_progress(tools, sample_mp4, tmp_path, run_worker):
    from core.media import AudioOptions
    from gui.worker import ConversionWorker

    out = tmp_path / "fp.mp3"
    worker = ConversionWorker([(str(sample_mp4), str(out), "mp3")], AudioOptions(), tools)
    fprogs = []
    worker.fileProgress.connect(fprogs.append)

    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert fprogs and fprogs[-1] == 1.0         # 현재 파일 100%로 마무리


# ----- 예상 크기: 실제 파일 길이 조회 + 추정 -----
@pytest.mark.ffmpeg
@pytest.mark.gui
def test_backend_estimate_with_real_file(qapp, sample_mp4):
    from gui.backend import Backend

    b = Backend()
    b.addUrls([sample_mp4.as_uri()])         # 실제 3초 mp4 → 길이 동기 조회
    b.setOutputFormat("mp3")
    b.updateEstimate({"bitrate": "192k"})
    # 192k * ~3s / 8 ≈ 72KB → "KB" 단위 예상 크기 표시
    assert b.estimatedSize.startswith("예상 출력 크기")
    assert "KB" in b.estimatedSize


# ----- C8/C9: 이미지↔pdf (ffmpeg 불필요) -----
@pytest.mark.gui
def test_worker_images_to_pdf(qapp, tmp_path, run_worker):
    pytest.importorskip("PIL")
    from PIL import Image

    from core.image import ImageOptions
    from gui.worker import ConversionWorker

    imgs = []
    for i, c in enumerate([(1, 2, 3), (4, 5, 6)]):
        p = tmp_path / f"p{i}.png"
        Image.new("RGB", (50, 50), c).save(p)
        imgs.append(str(p))
    out = tmp_path / "album.pdf"

    worker = ConversionWorker([(imgs, str(out), "pdf")], ImageOptions(), None)
    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.gui
def test_worker_pdf_to_images(qapp, tmp_path, run_worker):
    pytest.importorskip("PIL")
    pytest.importorskip("pypdfium2")
    from PIL import Image

    from core.image import ImageOptions, images_to_pdf
    from gui.worker import ConversionWorker

    a = tmp_path / "a.png"
    Image.new("RGB", (60, 60), (9, 9, 9)).save(a)
    pdf = tmp_path / "d.pdf"
    images_to_pdf([str(a)], str(pdf))
    out = tmp_path / "d.png"

    worker = ConversionWorker([(str(pdf), str(out), "png")], ImageOptions(), None)
    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert out.exists()


# ----- C4: 이미지 → 이미지 (ffmpeg 불필요, tools=None) -----
@pytest.mark.gui
def test_worker_image_pipeline(qapp, tmp_path, run_worker):
    pytest.importorskip("PIL")
    from PIL import Image

    from core.image import ImageOptions
    from gui.worker import ConversionWorker

    src = tmp_path / "a.png"
    Image.new("RGB", (80, 60), (0, 128, 255)).save(src)
    out = tmp_path / "a.jpg"

    worker = ConversionWorker([(str(src), str(out), "jpg")], ImageOptions(quality=80), None)
    res = run_worker(worker)
    assert res.get("ok") is True, res
    assert out.exists() and out.stat().st_size > 0
