"""출력 파일 크기 추정 및 사람이 읽는 크기 포맷.

추정은 **오디오 출력**만 신뢰성 있게 한다(비트레이트×길이, 무손실은 PCM 계산).
영상/이미지는 실제 인코딩 전에는 정확한 추정이 어려워 None을 반환한다.
"""
from __future__ import annotations

from core.registry import MediaKind, kind_of


def format_size(num: int | None) -> str:
    """바이트 → 사람이 읽는 문자열. None/음수는 빈 문자열."""
    if num is None or num < 0:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(num)
    i = 0
    while f >= 1024 and i < len(units) - 1:
        f /= 1024
        i += 1
    if i == 0:
        return f"{int(f)} {units[i]}"
    return f"{f:.1f} {units[i]}"


def _bitrate_kbps(bitrate, default: int = 192) -> int:
    if not bitrate:
        return default
    try:
        return int(str(bitrate).lower().rstrip("k"))
    except ValueError:
        return default


def estimate_output_bytes(out_ext: str, options: dict, durations) -> int | None:
    """오디오 출력의 예상 크기(바이트). 추정 불가면 None.

    durations: 입력 파일별 길이(초) 리스트. 하나라도 None이면 추정 불가.
    """
    if kind_of(out_ext) != MediaKind.AUDIO:
        return None
    if not durations or any(d is None for d in durations):
        return None

    total = sum(durations)
    ext = out_ext.lower()
    sr = int(options.get("sampleRate") or 0) or 44100
    ch = int(options.get("channels") or 0) or 2

    if ext in ("wav", "aiff"):
        return int(sr * ch * 2 * total)          # 16-bit PCM
    if ext == "flac":
        return int(sr * ch * 2 * total * 0.6)    # 무손실 압축 ≈ 60%
    # 손실 코덱: 목표 비트레이트 기반
    kbps = _bitrate_kbps(options.get("bitrate"))
    return int(kbps * 1000 / 8 * total)
