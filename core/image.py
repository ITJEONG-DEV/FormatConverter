"""Pillow 기반 이미지 변환 (C4: 이미지 → 이미지).

ffmpeg 와 달리 인프로세스로 즉시 변환한다. docs/DESIGN.md C4 참고.
"""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

# HEIC 입력 지원은 pillow-heif 플러그인이 있을 때만 활성화(선택적).
try:  # pragma: no cover - 플러그인 설치 환경에서만
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:  # noqa: BLE001
    pass

# 출력 확장자 -> Pillow 저장 포맷
IMAGE_FORMATS: dict[str, str] = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "tiff": "TIFF",
    "ico": "ICO",
}

# 투명도(알파)를 지원하지 않는 포맷 → RGB로 변환 필요
_NO_ALPHA = {"JPEG", "BMP"}


@dataclass
class ImageOptions:
    quality: int | None = None       # jpg/webp 품질 1~100
    resolution: str | None = None    # "720"(높이) 또는 "1280x720". None=원본


def _resize(img: "Image.Image", resolution: str) -> "Image.Image":
    res = resolution.strip().lower()
    w, h = img.size
    if "x" in res:
        nw, _, nh = res.partition("x")
        size = (int(nw), int(nh))
    else:
        new_h = int(res)
        new_w = max(1, round(w * new_h / h))
        size = (new_w, new_h)
    return img.resize(size, Image.Resampling.LANCZOS)


def convert_image(input_path: str, output_path: str, out_ext: str, opt: ImageOptions) -> None:
    fmt = IMAGE_FORMATS.get(out_ext.lower(), out_ext.upper())

    with Image.open(input_path) as img:
        img.load()

        if opt.resolution:
            img = _resize(img, opt.resolution)

        save_kwargs: dict = {}
        if fmt in _NO_ALPHA and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        if fmt in ("JPEG", "WEBP") and opt.quality:
            save_kwargs["quality"] = int(opt.quality)

        img.save(output_path, format=fmt, **save_kwargs)
