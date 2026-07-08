"""FFmpeg 기반 변환 명령 생성.

- 오디오: 영상→음원(C2), 음원→음원(C3)  (docs/DESIGN.md §9)
- 비디오: 영상→영상(C1)                  (docs/DESIGN.md §8)
"""
from __future__ import annotations

from dataclasses import dataclass

from core.registry import MediaKind, kind_of

# 출력 확장자 -> (코덱, 손실압축 여부)
AUDIO_CODECS: dict[str, tuple[str, bool]] = {
    "mp3": ("libmp3lame", True),
    "aac": ("aac", True),
    "m4a": ("aac", True),
    "ogg": ("libvorbis", True),
    "opus": ("libopus", True),
    "wma": ("wmav2", True),
    "wav": ("pcm_s16le", False),
    "aiff": ("pcm_s16be", False),
    "flac": ("flac", False),
}


@dataclass
class AudioOptions:
    """UI 고급 옵션에 대응. None/0 이면 '원본 유지' 또는 미적용."""
    bitrate: str | None = "192k"      # 예: "192k". 무손실 코덱에는 무시됨
    vbr_quality: int | None = None    # mp3 VBR (-q:a 0~9). 설정 시 bitrate 무시
    sample_rate: int | None = None    # 예: 44100. None=원본
    channels: int | None = None       # 1=모노, 2=스테레오. None=원본
    volume_db: float = 0.0            # 볼륨 증감(dB)
    normalize: bool = False           # loudnorm
    trim_start: float | None = None   # 시작(초)
    trim_end: float | None = None     # 끝(초)
    fade_in: float | None = None      # 페이드 인(초)
    fade_out: float | None = None     # 페이드 아웃(초)


def segment_duration(total: float | None, opt: AudioOptions) -> float | None:
    """진행률 계산용, 실제 변환 구간 길이(초)."""
    if total is None:
        return None
    start = opt.trim_start or 0.0
    end = opt.trim_end if opt.trim_end is not None else total
    return max(0.0, end - start)


def _audio_filters(opt: AudioOptions, seg_dur: float | None) -> str:
    filters: list[str] = []
    if opt.volume_db and opt.volume_db != 0.0:
        filters.append(f"volume={opt.volume_db}dB")
    if opt.normalize:
        filters.append("loudnorm")
    if opt.fade_in:
        filters.append(f"afade=t=in:st=0:d={opt.fade_in}")
    if opt.fade_out and seg_dur:
        start = max(0.0, seg_dur - opt.fade_out)
        filters.append(f"afade=t=out:st={start}:d={opt.fade_out}")
    return ",".join(filters)


def build_audio_command(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    out_ext: str,
    opt: AudioOptions,
    seg_dur: float | None = None,
) -> list[str]:
    codec, lossy = AUDIO_CODECS.get(out_ext.lower(), ("libmp3lame", True))

    args = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]

    # 구간 자르기: 입력 옵션으로 두면 -to 가 입력 파일 절대 타임스탬프 기준
    if opt.trim_start:
        args += ["-ss", str(opt.trim_start)]
    if opt.trim_end is not None:
        args += ["-to", str(opt.trim_end)]

    args += ["-i", input_path]

    # 영상 트랙 제거(음원 출력)
    args += ["-vn"]

    # 코덱
    args += ["-c:a", codec]

    # 비트레이트 / VBR (손실 코덱만)
    if lossy:
        if opt.vbr_quality is not None:
            args += ["-q:a", str(opt.vbr_quality)]
        elif opt.bitrate:
            args += ["-b:a", opt.bitrate]

    # 샘플레이트 / 채널
    if opt.sample_rate:
        args += ["-ar", str(opt.sample_rate)]
    if opt.channels:
        args += ["-ac", str(opt.channels)]

    # 오디오 필터
    chain = _audio_filters(opt, seg_dur)
    if chain:
        args += ["-af", chain]

    # 진행률 파이프
    args += ["-progress", "pipe:1", "-nostats"]

    args += [output_path]
    return args


# ---------------------------------------------------------------------------
# 비디오 (C1: 영상 → 영상)
# ---------------------------------------------------------------------------

# 출력 컨테이너 -> (기본 비디오 코덱, 기본 오디오 코덱)
VIDEO_CODECS: dict[str, tuple[str, str]] = {
    "mp4": ("libx264", "aac"),
    "mkv": ("libx264", "aac"),
    "mov": ("libx264", "aac"),
    "m4v": ("libx264", "aac"),
    "webm": ("libvpx-vp9", "libopus"),
    "avi": ("mpeg4", "libmp3lame"),
    "wmv": ("wmv2", "wmav2"),
    "flv": ("libx264", "aac"),
    "mpeg": ("mpeg2video", "mp2"),
    "ts": ("libx264", "aac"),
    "3gp": ("libx264", "aac"),
}


@dataclass
class VideoOptions:
    """영상→영상 변환 옵션. None/0 이면 '원본 유지' 또는 미적용."""
    video_codec: str | None = None    # None=컨테이너 기본
    crf: int | None = None            # 품질(낮을수록 고화질). x264/x265/vp9
    video_bitrate: str | None = None  # crf 대신 목표 비트레이트(예: "4M")
    resolution: str | None = None     # "720"(높이) 또는 "1280x720". None=원본
    fps: int | None = None            # None=원본
    audio_codec: str | None = None    # None=컨테이너 기본
    audio_bitrate: str | None = "192k"
    trim_start: float | None = None
    trim_end: float | None = None


def _scale_filter(resolution: str | None) -> str | None:
    """resolution 문자열을 ffmpeg scale 필터로 변환.

    "720" -> scale=-2:720 (가로는 비율 유지, 2의 배수)
    "1280x720" -> scale=1280:720
    """
    if not resolution:
        return None
    res = resolution.strip().lower()
    if "x" in res:
        w, _, h = res.partition("x")
        return f"scale={w}:{h}"
    return f"scale=-2:{res}"


def build_video_command(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    out_ext: str,
    opt: VideoOptions,
    seg_dur: float | None = None,
) -> list[str]:
    vcodec, acodec = VIDEO_CODECS.get(out_ext.lower(), ("libx264", "aac"))

    args = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]

    if opt.trim_start:
        args += ["-ss", str(opt.trim_start)]
    if opt.trim_end is not None:
        args += ["-to", str(opt.trim_end)]

    args += ["-i", input_path]

    # 비디오
    args += ["-c:v", opt.video_codec or vcodec]
    if opt.crf is not None:
        args += ["-crf", str(opt.crf)]
    elif opt.video_bitrate:
        args += ["-b:v", opt.video_bitrate]

    vf = _scale_filter(opt.resolution)
    if vf:
        args += ["-vf", vf]
    if opt.fps:
        args += ["-r", str(opt.fps)]

    # 오디오 (영상의 오디오 트랙 재인코딩)
    args += ["-c:a", opt.audio_codec or acodec]
    if opt.audio_bitrate:
        args += ["-b:a", opt.audio_bitrate]

    args += ["-progress", "pipe:1", "-nostats"]
    args += [output_path]
    return args


# ---------------------------------------------------------------------------
# 영상 → 이미지 (C5: gif/webp 애니메이션 · 단일 프레임 추출)
# ---------------------------------------------------------------------------

# 애니메이션으로 만들 출력(구간 전체) vs 단일 프레임 추출
_ANIMATED_IMAGE = {"gif", "webp"}


@dataclass
class VideoToImageOptions:
    fps: int | None = None            # gif/webp 프레임레이트(None=10)
    resolution: str | None = None     # "480"(높이) 또는 "640x480". None=원본
    trim_start: float | None = None   # 애니: 시작 / 단일프레임: 추출 시점(초)
    trim_end: float | None = None     # 애니: 끝(초)


def build_video_to_image_command(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    out_ext: str,
    opt: VideoToImageOptions,
    seg_dur: float | None = None,
) -> list[str]:
    ext = out_ext.lower()
    animated = ext in _ANIMATED_IMAGE

    args = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]

    if opt.trim_start:
        args += ["-ss", str(opt.trim_start)]
    if animated and opt.trim_end is not None:
        args += ["-to", str(opt.trim_end)]

    args += ["-i", input_path]

    scale = _scale_filter(opt.resolution)

    if animated:
        fps = opt.fps or 10
        vf = f"fps={fps}"
        if scale:
            vf += f",{scale}"
        if ext == "gif":
            # 단일 패스로 팔레트 생성·적용 → 고품질 GIF
            vf += ",split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
            args += ["-vf", vf, "-loop", "0"]
        else:  # 애니메이션 webp
            args += ["-vf", vf, "-loop", "0", "-an"]
        args += ["-progress", "pipe:1", "-nostats"]
    else:
        # 단일 프레임 추출 (png/jpg/bmp/tiff)
        args += ["-frames:v", "1"]
        if scale:
            args += ["-vf", scale]

    args += [output_path]
    return args


# ---------------------------------------------------------------------------
# 이미지 시퀀스 → 영상 (C6: 다중 이미지 → 단일 영상, concat 데멀서)
# ---------------------------------------------------------------------------


@dataclass
class VideoSequenceOptions:
    seconds_per_image: float = 1.0    # 각 이미지 표시 시간(초)
    resolution: str | None = None     # 출력 프레임 크기 "1280x720". None=1280x720
    fps: int = 30                     # 출력 영상 fps


def _seq_dims(resolution: str | None) -> tuple[int, int]:
    res = (resolution or "1280x720").lower()
    if "x" in res:
        w, _, h = res.partition("x")
        return int(w), int(h)
    h = int(res)
    return (int(round(h * 16 / 9)) // 2 * 2, h)


def _concat_escape(path) -> str:
    # concat 데멀서: 경로는 정슬래시, 작은따옴표는 '\'' 로 이스케이프
    return str(path).replace("\\", "/").replace("'", "'\\''")


def write_concat_file(images, seconds_per_image: float, dest: str) -> None:
    """concat 데멀서용 목록 파일 작성. 마지막 이미지는 잘리지 않도록 한 번 더 기재."""
    lines = ["ffconcat version 1.0"]
    for img in images:
        lines.append(f"file '{_concat_escape(img)}'")
        lines.append(f"duration {seconds_per_image}")
    if images:
        lines.append(f"file '{_concat_escape(images[-1])}'")
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_image_sequence_command(
    ffmpeg: str,
    concat_path: str,
    output_path: str,
    out_ext: str,
    opt: VideoSequenceOptions,
) -> list[str]:
    vcodec, _ = VIDEO_CODECS.get(out_ext.lower(), ("libx264", "aac"))
    w, h = _seq_dims(opt.resolution)
    # 크기가 다른 이미지도 letterbox 로 통일(concat 은 동일 크기 요구) + 호환 픽셀포맷
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps={opt.fps},format=yuv420p"
    )
    return [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", concat_path,
        "-vf", vf, "-c:v", vcodec,
        "-progress", "pipe:1", "-nostats", output_path,
    ]


# ---------------------------------------------------------------------------
def build_command(
    ffmpeg: str,
    input_path: str,
    output_path: str,
    out_ext: str,
    opt,
    seg_dur: float | None = None,
) -> list[str]:
    """출력 종류에 따라 오디오/비디오/이미지(영상소스) 명령 생성으로 라우팅."""
    out_kind = kind_of(out_ext)
    if out_kind == MediaKind.VIDEO:
        return build_video_command(ffmpeg, input_path, output_path, out_ext, opt, seg_dur)
    if out_kind == MediaKind.IMAGE:
        return build_video_to_image_command(ffmpeg, input_path, output_path, out_ext, opt, seg_dur)
    return build_audio_command(ffmpeg, input_path, output_path, out_ext, opt, seg_dur)
