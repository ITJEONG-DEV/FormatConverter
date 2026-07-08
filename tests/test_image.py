"""① 단위 + 변환 테스트 — 이미지 변환 (core/image.py, Pillow).

Pillow 미설치 시 자동 skip.
"""
import pytest

pytest.importorskip("PIL")

from PIL import Image

from core.image import ImageOptions, _resize, convert_image


@pytest.fixture
def png_rgba(tmp_path):
    """알파 채널 있는 200x100 PNG 생성."""
    p = tmp_path / "src.png"
    Image.new("RGBA", (200, 100), (255, 0, 0, 128)).save(p)
    return p


def test_png_to_jpg_drops_alpha(png_rgba, tmp_path):
    out = tmp_path / "o.jpg"
    convert_image(str(png_rgba), str(out), "jpg", ImageOptions(quality=85))
    assert out.exists() and out.stat().st_size > 0
    with Image.open(out) as im:
        assert im.format == "JPEG"
        assert im.mode == "RGB"          # 알파 제거됨


def test_png_to_webp(png_rgba, tmp_path):
    out = tmp_path / "o.webp"
    convert_image(str(png_rgba), str(out), "webp", ImageOptions())
    with Image.open(out) as im:
        assert im.format == "WEBP"


def test_resize_by_height(png_rgba, tmp_path):
    out = tmp_path / "o.png"
    convert_image(str(png_rgba), str(out), "png", ImageOptions(resolution="50"))
    with Image.open(out) as im:
        assert im.height == 50
        assert im.width == 100           # 200x100 → 비율 유지(가로 100)


def test_resize_exact():
    img = Image.new("RGB", (200, 100))
    out = _resize(img, "1280x720")
    assert out.size == (1280, 720)


def test_resize_keep_aspect():
    img = Image.new("RGB", (200, 100))
    out = _resize(img, "50")
    assert out.size == (100, 50)


def test_convert_to_bmp(png_rgba, tmp_path):
    out = tmp_path / "o.bmp"
    convert_image(str(png_rgba), str(out), "bmp", ImageOptions())
    with Image.open(out) as im:
        assert im.format == "BMP"
