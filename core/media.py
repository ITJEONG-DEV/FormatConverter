"""FFmpeg 기반 오디오 변환(영상→음원 C2, 음원→음원 C3) 명령 생성.

docs/DESIGN.md §9 (mp4→mp3 고급 옵션)에 대응한다.
"""
from __future__ import annotations

from dataclasses import dataclass

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
