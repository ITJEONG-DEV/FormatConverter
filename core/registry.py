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
    DOCUMENT = "document"


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
_DOCUMENT = [
    "pdf", "docx", "doc", "odt", "rtf", "txt", "html",
    "xlsx", "xls", "csv", "ods", "pptx", "ppt", "odp",
]

FORMATS: dict[str, Format] = {}
for _ext in _VIDEO:
    FORMATS[_ext] = Format(_ext, MediaKind.VIDEO)
for _ext in _AUDIO:
    FORMATS[_ext] = Format(_ext, MediaKind.AUDIO)
for _ext in _IMAGE:
    # 컨테이너 특성상 ico/heic 등은 출력 지원이 제한적이지만 데이터로만 표시
    FORMATS[_ext] = Format(_ext, MediaKind.IMAGE)
for _ext in _DOCUMENT:
    FORMATS[_ext] = Format(_ext, MediaKind.DOCUMENT)


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
    (MediaKind.DOCUMENT, MediaKind.DOCUMENT),  # C7 (문서→문서, LibreOffice)
    (MediaKind.IMAGE, MediaKind.DOCUMENT),     # C8 (이미지→pdf, Pillow)
    (MediaKind.DOCUMENT, MediaKind.IMAGE),     # C9 (pdf→이미지, pypdfium2)
}

# 특정 경로에서만 허용되는 출력 포맷(및 표시 순서). 없으면 해당 종류 전체를 우선순위로 정렬.
# - 비현실적 조합 방지(이미지→pdf만, pdf→이미지만)
# - 대표 포맷을 앞으로(영상→이미지는 gif 우선)
ROUTE_OUTPUTS = {
    (MediaKind.VIDEO, MediaKind.IMAGE): ["gif", "webp", "png", "jpg", "jpeg", "bmp", "tiff"],
    (MediaKind.IMAGE, MediaKind.DOCUMENT): ["pdf"],
    (MediaKind.DOCUMENT, MediaKind.IMAGE): ["png", "jpg", "jpeg", "webp", "tiff", "bmp"],
}

# 특정 입력 확장자에서만 성립하는 경로(없으면 종류 전체 허용).
# 문서→이미지는 pdf 렌더링만 가능(pypdfium2는 pdf만 연다).
ROUTE_INPUT_EXTS = {
    (MediaKind.DOCUMENT, MediaKind.IMAGE): {"pdf"},
}


def _route_allows_input(route, input_ext: str) -> bool:
    allowed = ROUTE_INPUT_EXTS.get(route)
    return allowed is None or input_ext in allowed


# 문서→문서는 계열이 맞아야 실제 변환된다(워드→스프레드시트 등은 무의미).
# 입력 확장자의 계열 + 공통(pdf)만 출력으로 노출한다.
_DOC_FAMILY = {
    "docx": "word", "doc": "word", "odt": "word", "rtf": "word", "txt": "word", "html": "word",
    "xlsx": "sheet", "xls": "sheet", "ods": "sheet", "csv": "sheet",
    "pptx": "pres", "ppt": "pres", "odp": "pres",
    "pdf": "pdf",
}
_FAMILY_OUTPUTS = {
    "word":  ["pdf", "docx", "odt", "rtf", "txt", "html", "doc"],
    "sheet": ["pdf", "xlsx", "ods", "csv", "html", "xls"],
    "pres":  ["pdf", "pptx", "odp", "ppt"],
    "pdf":   [],   # pdf→문서 변환은 신뢰도 낮아 제공 안 함(pdf→이미지만 지원)
}


def _document_targets(input_ext: str) -> list[str]:
    return list(_FAMILY_OUTPUTS.get(_DOC_FAMILY.get(input_ext, ""), []))


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
    # document
    "pdf": 0, "docx": 1, "xlsx": 2, "pptx": 3, "odt": 4, "txt": 5, "html": 6,
    "rtf": 7, "doc": 8, "xls": 9, "csv": 10, "ods": 11, "ppt": 12, "odp": 13,
}


# 출력 종류(카테고리) 표시 라벨
KIND_LABEL = {
    MediaKind.VIDEO: "영상",
    MediaKind.AUDIO: "음원",
    MediaKind.IMAGE: "이미지",
    MediaKind.DOCUMENT: "문서",
}
_KIND_ORDER = [MediaKind.VIDEO, MediaKind.AUDIO, MediaKind.IMAGE, MediaKind.DOCUMENT]


def output_categories_for(input_ext: str) -> list[MediaKind]:
    """입력에 대해 가능한 출력 종류(카테고리) 목록. 같은 종류를 먼저.

    실제 출력 포맷이 하나도 없는 종류는 제외한다(예: pdf→문서).
    """
    input_ext = input_ext.lower().lstrip(".")
    kind = kind_of(input_ext)
    if kind is None:
        return []
    dsts = {
        dst for src, dst in IMPLEMENTED_ROUTES
        if src == kind and _route_allows_input((src, dst), input_ext)
    }
    ordered = sorted(dsts, key=lambda k: (0 if k == kind else 1, _KIND_ORDER.index(k)))
    return [k for k in ordered if output_formats_for(input_ext, k)]


def output_formats_for(input_ext: str, category: MediaKind | None = None) -> list[str]:
    """입력 확장자에 대해 구현된 출력 포맷 목록.

    category 를 주면 해당 종류만, 없으면 전체(같은 종류 먼저).
    경로별 제한(ROUTE_OUTPUTS)이 있으면 그 목록·순서를 그대로 쓰고,
    없으면 흔한 포맷 우선 + 동일 확장자는 뒤로 정렬한다.
    """
    input_ext = input_ext.lower().lstrip(".")
    kind = kind_of(input_ext)
    if kind is None:
        return []

    dsts = [
        d for s, d in IMPLEMENTED_ROUTES
        if s == kind and _route_allows_input((s, d), input_ext)
    ]
    dsts = sorted(set(dsts), key=lambda d: (0 if d == kind else 1, _KIND_ORDER.index(d)))

    def _sort_key(ext: str):
        return (ext == input_ext, _PRIORITY.get(ext, 99), ext)

    result: list[str] = []
    seen: set[str] = set()
    for dst in dsts:
        if category is not None and dst != category:
            continue
        route = (kind, dst)
        if route == (MediaKind.DOCUMENT, MediaKind.DOCUMENT):
            exts = sorted(_document_targets(input_ext), key=_sort_key)  # 계열 제한
        elif route in ROUTE_OUTPUTS:
            exts = list(ROUTE_OUTPUTS[route])           # 명시된 순서 유지
        else:
            exts = sorted(
                (f.ext for f in FORMATS.values() if f.kind == dst and f.can_output),
                key=_sort_key,
            )
        for e in exts:
            if e in FORMATS and e not in seen:
                seen.add(e)
                result.append(e)
    return result
