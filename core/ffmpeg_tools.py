"""FFmpeg / FFprobe 실행 파일 탐색 및 미디어 정보 조회."""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Windows에서 콘솔 창이 깜빡이지 않도록
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# 프로젝트 루트/bin 우선 탐색
_BIN_DIR = Path(__file__).resolve().parent.parent / "bin"


@dataclass(frozen=True)
class Tools:
    ffmpeg: str
    ffprobe: str


class FFmpegNotFound(Exception):
    pass


def _locate(name: str) -> str | None:
    exe = name + (".exe" if sys.platform == "win32" else "")
    local = _BIN_DIR / exe
    if local.exists():
        return str(local)
    found = shutil.which(name)
    return found


def find_tools() -> Tools:
    """ffmpeg/ffprobe 경로를 찾는다. 없으면 FFmpegNotFound."""
    ffmpeg = _locate("ffmpeg")
    ffprobe = _locate("ffprobe")
    if not ffmpeg:
        raise FFmpegNotFound(
            "ffmpeg 실행 파일을 찾을 수 없습니다. bin/ 폴더에 넣거나 PATH에 등록하세요."
        )
    # ffprobe가 없으면 진행률 계산만 불가 (변환은 가능)
    return Tools(ffmpeg=ffmpeg, ffprobe=ffprobe or "")


def probe_duration(ffprobe: str, path: str) -> float | None:
    """미디어 전체 길이(초). 실패 시 None."""
    if not ffprobe:
        return None
    try:
        out = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True, text=True, creationflags=_NO_WINDOW,
        )
        value = out.stdout.strip()
        return float(value) if value else None
    except (ValueError, OSError):
        return None
