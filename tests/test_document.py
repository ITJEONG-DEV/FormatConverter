"""① 단위 + ③ 통합 — 문서 변환 (core/document.py, LibreOffice C7)."""
from pathlib import Path

import pytest

from core import document as doc


def test_find_soffice_missing(monkeypatch):
    monkeypatch.setattr(doc.shutil, "which", lambda name: None)
    monkeypatch.setattr(doc, "_candidate_paths", lambda: [])
    with pytest.raises(doc.SofficeNotFound):
        doc.find_soffice()


def test_find_soffice_from_path(monkeypatch):
    monkeypatch.setattr(
        doc.shutil, "which",
        lambda name: "/usr/bin/soffice" if name == "soffice" else None,
    )
    assert doc.find_soffice() == "/usr/bin/soffice"


def test_build_convert_command():
    cmd = doc.build_convert_command("soffice", "/in/a.docx", "pdf", "/out")
    assert cmd[0] == "soffice"
    assert "--headless" in cmd
    assert cmd[cmd.index("--convert-to") + 1] == "pdf"
    assert cmd[cmd.index("--outdir") + 1] == "/out"
    assert cmd[-1] == "/in/a.docx"


def test_build_convert_command_with_profile(tmp_path):
    cmd = doc.build_convert_command("soffice", "a.docx", "pdf", "out", str(tmp_path))
    assert any(a.startswith("-env:UserInstallation=file://") for a in cmd)


def test_expected_output():
    assert doc.expected_output("/in/report.docx", "pdf", "/out") == str(
        Path("/out/report.pdf")
    )


# --- registry: 문서 카테고리/포맷 ---
def test_registry_document_routing():
    from core.registry import (
        MediaKind, is_supported_input, kind_of, output_categories_for, output_formats_for,
    )
    assert kind_of("docx") == MediaKind.DOCUMENT
    assert is_supported_input("docx")
    assert output_categories_for("docx") == [MediaKind.DOCUMENT]
    outs = output_formats_for("docx")
    assert outs[0] == "pdf"                 # 흔한 대상 우선
    assert "docx" not in outs[:1]           # 동일 확장자는 기본값 아님
    assert "mp4" not in outs and "mp3" not in outs


# --- 통합: 실제 LibreOffice 변환 (없으면 skip) ---
@pytest.mark.soffice
def test_txt_to_pdf(soffice, tmp_path):
    src = tmp_path / "note.txt"
    src.write_text("Hello FormatConverter\n문서 변환 테스트", encoding="utf-8")
    out = tmp_path / "note.pdf"

    import subprocess
    cmd = doc.build_convert_command(soffice, str(src), "pdf", str(tmp_path),
                                    str(tmp_path / "profile"))
    subprocess.run(cmd, capture_output=True, timeout=180)
    assert Path(doc.expected_output(str(src), "pdf", str(tmp_path))).exists()
