"""pypdfium2 기반 PDF → 이미지 렌더링 (C9).

PDF 각 페이지를 이미지로 렌더링한다. 여러 페이지면 파일이 여러 개 생성된다
(<stem>_p1.png, <stem>_p2.png ...). pypdfium2는 BSD/Apache 라이선스라 배포에 안전하다.
"""
from __future__ import annotations

from pathlib import Path

# JPEG/BMP는 알파를 지원하지 않아 RGB로 변환 필요
_NO_ALPHA = {"jpg", "jpeg", "bmp"}


def pdf_engine_available() -> bool:
    try:
        import pypdfium2  # noqa: F401
        return True
    except ImportError:
        return False


def render_pdf_to_images(
    pdf_path: str, out_dir: str, out_ext: str, dpi: int = 150,
) -> list[str]:
    import pypdfium2 as pdfium

    ext = out_ext.lower()
    scale = dpi / 72.0
    stem = Path(pdf_path).stem
    doc = pdfium.PdfDocument(pdf_path)
    outputs: list[str] = []
    try:
        n = len(doc)
        if n == 0:
            raise RuntimeError("PDF에 페이지가 없습니다.")
        for i in range(n):
            img = doc[i].render(scale=scale).to_pil()
            if ext in _NO_ALPHA and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            name = f"{stem}.{ext}" if n == 1 else f"{stem}_p{i + 1}.{ext}"
            path = str(Path(out_dir) / name)
            img.save(path)
            outputs.append(path)
    finally:
        doc.close()
    return outputs
