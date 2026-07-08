"""LibreOffice(headless) 기반 문서 변환 (C7: 문서 → 문서).

soffice를 외부 엔진으로 사용한다(미디어의 ffmpeg, 이미지의 Pillow와 같은 패턴).
`soffice --headless --convert-to <ext> --outdir <dir> <input>` 로 변환하며,
결과 파일은 <outdir>/<입력스템>.<ext> 로 생성된다.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


class SofficeNotFound(Exception):
    pass


def _candidate_paths() -> list[str]:
    paths: list[str] = []
    if sys.platform == "win32":
        for base in (
            r"C:\Program Files\LibreOffice\program",
            r"C:\Program Files (x86)\LibreOffice\program",
        ):
            paths.append(str(Path(base) / "soffice.exe"))
    elif sys.platform == "darwin":
        paths.append("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    else:
        paths += ["/usr/bin/soffice", "/usr/local/bin/soffice"]
    return paths


def find_soffice() -> str:
    """LibreOffice 실행 파일 경로. 없으면 SofficeNotFound."""
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for p in _candidate_paths():
        if Path(p).exists():
            return p
    raise SofficeNotFound(
        "LibreOffice를 찾을 수 없습니다. 문서 변환에는 LibreOffice가 필요합니다 "
        "(libreoffice.org에서 설치)."
    )


def build_convert_command(
    soffice: str,
    input_path: str,
    out_ext: str,
    outdir: str,
    user_profile: str | None = None,
) -> list[str]:
    args = [soffice, "--headless", "--norestore"]
    if user_profile:
        # 이미 실행 중인 LibreOffice 인스턴스와의 프로필 잠금 충돌 회피
        args.append("-env:UserInstallation=" + Path(user_profile).as_uri())
    args += ["--convert-to", out_ext, "--outdir", outdir, input_path]
    return args


def expected_output(input_path: str, out_ext: str, outdir: str) -> str:
    """soffice가 생성할 결과 파일 경로."""
    return str(Path(outdir) / f"{Path(input_path).stem}.{out_ext.lower()}")
