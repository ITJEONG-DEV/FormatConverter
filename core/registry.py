"""포맷 / 카테고리 / 라우팅 정의.

UI는 여기에 "이 입력 포맷으로 가능한 출력 포맷 목록"만 물어보면 되고,
새 포맷·엔진 추가 시 코드가 아니라 이 데이터만 늘리면 된다.
자세한 설계는 docs/DESIGN.md 참고.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MediaKind(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


@dataclass(frozen=True)
class Format:
    ext: str
    kind: MediaKind
    can_input: bool = True
    can_output: bool = True


# --- 확장자 정의 ---
_VIDEO = ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv", "m4v", "mpeg", "ts", "3gp"]
_AUDIO = ["mp3", "wav", "aac", "flac", "ogg", "m4a", "wma", "opus", "aiff"]
_IMAGE = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "ico", "heic"]

FORMATS: dict[str, Format] = {}
for _ext in _VIDEO:
    FORMATS[_ext] = Format(_ext, MediaKind.VIDEO)
for _ext in _AUDIO:
    FORMATS[_ext] = Format(_ext, MediaKind.AUDIO)
for _ext in _IMAGE:
    # 컨테이너 특성상 ico/heic 등은 출력 지원이 제한적이지만 데이터로만 표시
    FORMATS[_ext] = Format(_ext, MediaKind.IMAGE)


# --- 변환 카테고리(입력 종류, 출력 종류) ---
# 설계상 정의된 전체 경로 (docs/DESIGN.md C1~C6)
ALL_ROUTES = {
    (MediaKind.VIDEO, MediaKind.VIDEO),   # C1
    (MediaKind.VIDEO, MediaKind.AUDIO),   # C2
    (MediaKind.AUDIO, MediaKind.AUDIO),   # C3
    (MediaKind.IMAGE, MediaKind.IMAGE),   # C4
}

# 실제 구현된 경로
IMPLEMENTED_ROUTES = {
    (MediaKind.VIDEO, MediaKind.VIDEO),   # C1 (영상→영상)
    (MediaKind.VIDEO, MediaKind.AUDIO),   # C2 ★ (영상→음원)
    (MediaKind.AUDIO, MediaKind.AUDIO),   # C3 (음원→음원)
    (MediaKind.IMAGE, MediaKind.IMAGE),   # C4 (이미지→이미지, Pillow)
    (MediaKind.VIDEO, MediaKind.IMAGE),   # C5 (영상→이미지: gif/프레임)
    (MediaKind.IMAGE, MediaKind.VIDEO),   # C6 (이미지 시퀀스→영상)
}


def kind_of(ext: str) -> MediaKind | None:
    fmt = FORMATS.get(ext.lower().lstrip("."))
    return fmt.kind if fmt else None


def is_supported_input(ext: str) -> bool:
    """현재 구현된 경로 중 이 확장자를 입력으로 쓸 수 있는가."""
    kind = kind_of(ext)
    if kind is None:
        return False
    return any(src == kind for src, _dst in IMPLEMENTED_ROUTES)


# 흔한 포맷을 앞에 오도록 하는 정렬 우선순위(작을수록 먼저).
_PRIORITY = {
    # audio
    "mp3": 0, "aac": 1, "m4a": 2, "wav": 3, "flac": 4,
    "ogg": 5, "opus": 6, "aiff": 7, "wma": 8,
    # video
    "mp4": 0, "mkv": 1, "mov": 2, "webm": 3, "avi": 4, "m4v": 5,
    "flv": 6, "mpeg": 7, "ts": 8, "3gp": 9, "wmv": 10,
    # image
    "png": 0, "jpg": 1, "jpeg": 2, "webp": 3, "bmp": 4,
    "tiff": 5, "gif": 6, "ico": 7, "heic": 8,
}


def output_formats_for(input_ext: str) -> list[str]:
    """입력 확장자에 대해 현재 구현된 출력 포맷 목록.

    정렬: (1) 입력과 같은 종류를 먼저(영상→영상 우선), (2) 흔한 포맷 우선,
    (3) 입력과 동일한 확장자는 뒤로(예: mp4 입력의 기본 출력이 mp4→mp4가 되지 않게).
    """
    input_ext = input_ext.lower().lstrip(".")
    kind = kind_of(input_ext)
    if kind is None:
        return []
    dst_kinds = {dst for src, dst in IMPLEMENTED_ROUTES if src == kind}
    outs = [f for f in FORMATS.values() if f.kind in dst_kinds and f.can_output]
    outs.sort(key=lambda f: (
        0 if f.kind == kind else 1,      # 같은 종류 먼저
        f.ext == input_ext,              # 동일 확장자는 뒤로
        _PRIORITY.get(f.ext, 99),        # 흔한 포맷 우선
        f.ext,
    ))
    return [f.ext for f in outs]
