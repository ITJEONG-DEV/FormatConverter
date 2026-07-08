"""이미지↔pdf 변환 (C8: 이미지→pdf, C9: pdf→이미지)."""
from pathlib import Path

import pytest

from core.registry import MediaKind, output_categories_for, output_formats_for


# --- registry: 라우팅/카테고리 ---
def test_image_to_pdf_route():
    cats = output_categories_for("png")
    assert MediaKind.DOCUMENT in cats                  # 이미지→문서(pdf)
    outs = output_formats_for("png", MediaKind.DOCUMENT)
    assert outs == ["pdf"]                              # pdf만 허용


def test_pdf_to_image_route():
    cats = output_categories_for("pdf")
    assert cats[0] == MediaKind.DOCUMENT               # 같은 종류 먼저
    assert MediaKind.IMAGE in cats                     # pdf→이미지
    outs = output_formats_for("pdf", MediaKind.IMAGE)
    assert "png" in outs and "jpg" in outs
    assert "gif" not in outs and "ico" not in outs     # 제한된 목록


def test_video_to_image_gif_first():
    # 기능1: 영상→이미지에서 gif가 맨 앞
    outs = output_formats_for("mp4", MediaKind.IMAGE)
    assert outs[0] == "gif"
    assert "ico" not in outs and "heic" not in outs


# --- 엔진 단위 ---
def test_images_to_pdf(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    from core.image import images_to_pdf

    imgs = []
    for i, c in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        p = tmp_path / f"i{i}.png"
        Image.new("RGB", (60, 40), c).save(p)
        imgs.append(str(p))
    out = tmp_path / "album.pdf"
    images_to_pdf(imgs, str(out))
    assert out.exists() and out.stat().st_size > 0
    # 3페이지인지 확인
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(out))
    assert len(doc) == 3
    doc.close()


def test_pdf_to_images_multipage(tmp_path):
    pytest.importorskip("PIL")
    pytest.importorskip("pypdfium2")
    from PIL import Image

    from core.image import images_to_pdf
    from core.pdf import render_pdf_to_images

    # 2페이지 pdf 생성
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    Image.new("RGB", (80, 60), (255, 0, 0)).save(a)
    Image.new("RGB", (80, 60), (0, 0, 255)).save(b)
    pdf = tmp_path / "doc.pdf"
    images_to_pdf([str(a), str(b)], str(pdf))

    produced = render_pdf_to_images(str(pdf), str(tmp_path), "png", dpi=72)
    assert len(produced) == 2                          # 페이지마다 이미지 1개
    for p in produced:
        assert Path(p).exists()
    assert "doc_p1.png" in produced[0]


def test_pdf_to_images_single_page(tmp_path):
    pytest.importorskip("PIL")
    pytest.importorskip("pypdfium2")
    from PIL import Image

    from core.image import images_to_pdf
    from core.pdf import render_pdf_to_images

    a = tmp_path / "solo.png"
    Image.new("RGB", (80, 60), (0, 128, 0)).save(a)
    pdf = tmp_path / "one.pdf"
    images_to_pdf([str(a)], str(pdf))

    produced = render_pdf_to_images(str(pdf), str(tmp_path), "jpg", dpi=72)
    assert len(produced) == 1
    assert produced[0].endswith("one.jpg")             # 1페이지는 접미사 없음


def test_pdf_engine_available():
    from core.pdf import pdf_engine_available
    assert pdf_engine_available() is True              # pypdfium2 설치됨
