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


# ----- 비디오(C1) -----
from core.media import VideoOptions, build_video_command, build_command, _scale_filter


def vbuild(ext="mp4", seg=None, **kw):
    return build_video_command("ffmpeg", "in.mp4", f"out.{ext}", ext, VideoOptions(**kw), seg)


@pytest.mark.parametrize(
    "ext,vcodec,acodec",
    [
        ("mp4", "libx264", "aac"),
        ("mkv", "libx264", "aac"),
        ("webm", "libvpx-vp9", "libopus"),
        ("avi", "mpeg4", "libmp3lame"),
    ],
)
def test_video_codec_selection(ext, vcodec, acodec):
    c = vbuild(ext=ext)
    assert c[c.index("-c:v") + 1] == vcodec
    assert c[c.index("-c:a") + 1] == acodec


def test_scale_filter():
    assert _scale_filter("720") == "scale=-2:720"
    assert _scale_filter("1280x720") == "scale=1280:720"
    assert _scale_filter("") is None
    assert _scale_filter(None) is None


def test_video_resolution_and_fps():
    c = vbuild(resolution="720", fps=30)
    assert c[c.index("-vf") + 1] == "scale=-2:720"
    assert c[c.index("-r") + 1] == "30"


def test_video_crf_vs_bitrate():
    assert "-crf" in vbuild(crf=18)
    c = vbuild(video_bitrate="4M")
    assert "-crf" not in c
    assert c[c.index("-b:v") + 1] == "4M"


def test_video_trim_before_input():
    c = vbuild(trim_start=5, trim_end=10)
    i = c.index("-i")
    assert c.index("-ss") < i and c.index("-to") < i


def test_video_audio_bitrate():
    assert vbuild(audio_bitrate="128k")[vbuild(audio_bitrate="128k").index("-b:a") + 1] == "128k"


def test_build_command_routes_by_kind():
    # 비디오 출력 → -c:v 포함, 오디오 출력 → -vn 포함
    vc = build_command("ffmpeg", "in.mp4", "out.mkv", "mkv", VideoOptions())
    assert "-c:v" in vc and "-vn" not in vc
    ac = build_command("ffmpeg", "in.mp4", "out.mp3", "mp3", AudioOptions())
    assert "-vn" in ac and "-c:v" not in ac


# ----- C5: 영상 → 이미지 -----
from core.media import VideoToImageOptions, build_video_to_image_command


def v2i(ext="gif", seg=None, **kw):
    return build_video_to_image_command(
        "ffmpeg", "in.mp4", f"out.{ext}", ext, VideoToImageOptions(**kw), seg)


def test_gif_animated_palette():
    c = v2i("gif", fps=15, resolution="480", trim_start=1, trim_end=4)
    vf = c[c.index("-vf") + 1]
    assert "fps=15" in vf
    assert "scale=-2:480" in vf
    assert "palettegen" in vf and "paletteuse" in vf
    assert "-loop" in c
    i = c.index("-i")
    assert c.index("-ss") < i and c.index("-to") < i     # 구간을 입력측에 배치


def test_webp_animated():
    c = v2i("webp", fps=10)
    vf = c[c.index("-vf") + 1]
    assert "fps=10" in vf
    assert "-loop" in c and "-an" in c
    assert "palettegen" not in vf                        # webp는 팔레트 미사용


def test_single_frame_png():
    c = v2i("png", trim_start=5)
    assert c[c.index("-frames:v") + 1] == "1"
    assert "-to" not in c                                # 단일 프레임엔 종료시각 없음
    assert c.index("-ss") < c.index("-i")


def test_default_gif_fps():
    assert "fps=10" in v2i("gif")[v2i("gif").index("-vf") + 1]


def test_build_command_video_to_image():
    c = build_command("ffmpeg", "in.mp4", "out.gif", "gif", VideoToImageOptions())
    assert "palettegen" in c[c.index("-vf") + 1]         # 영상→이미지 경로로 라우팅
