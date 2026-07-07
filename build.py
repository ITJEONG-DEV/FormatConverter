"""
build.py
--------
PyInstaller 배포 빌드 스크립트. 두 가지 산출물을 만든다.

  full  : 폴더형(onedir) + ffmpeg 번들 포함  -> dist/FormatConverter/
  lite  : 단일파일(onefile), ffmpeg 미포함    -> dist/FormatConverter-lite.exe

사용법:
  python build.py            # full + lite 모두 빌드
  python build.py full       # 폴더형만
  python build.py lite       # 라이트(단일파일)만

사전 준비:
  pip install pyinstaller
  full 빌드는 bin/ffmpeg.exe, bin/ffprobe.exe 가 있어야 한다.
"""

import os
import sys

import PyInstaller.__main__

# CI 등 콘솔 인코딩이 UTF-8이 아닌 환경에서 한글 print가
# UnicodeEncodeError로 죽지 않도록 표준출력을 UTF-8로 재설정한다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "main.py")
ICON = os.path.join(ROOT, "assets", "app.ico")  # 있으면 자동 사용
QML_DIR = os.path.join(ROOT, "gui", "qml")
SEP = os.pathsep  # Windows ';'

# 버전은 version.py 단일 소스에서 가져온다.
sys.path.insert(0, ROOT)
try:
    from version import __version__
except Exception:
    __version__ = "0.0.0"

APP_TITLE = "FormatConverter"
APP_NAME = "FormatConverter"
LITE_NAME = "FormatConverter-lite"

# exe 파일 속성(자세히 탭)에 표시할 개발자명. 서명 인증서는 아니며 단순 표기용.
DEV_NAME = "ITJEONG-DEV"


def _version_tuple() -> tuple:
    nums = []
    for p in __version__.replace("-", ".").split("."):
        digits = "".join(c for c in p if c.isdigit())
        nums.append(int(digits) if digits else 0)
    return tuple((nums + [0, 0, 0, 0])[:4])


def _write_version_file() -> str:
    """PyInstaller용 Windows 버전 리소스 파일 생성(개발자명 등 메타데이터 포함)."""
    v = _version_tuple()
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    path = os.path.join(ROOT, "build", "version_info.txt")
    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={v}, prodvers={v},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('041204B0', [
        StringStruct('CompanyName', '{DEV_NAME}'),
        StringStruct('FileDescription', '{APP_TITLE}'),
        StringStruct('FileVersion', '{__version__}'),
        StringStruct('InternalName', '{APP_TITLE}'),
        StringStruct('OriginalFilename', '{APP_TITLE}.exe'),
        StringStruct('ProductName', '{APP_TITLE}'),
        StringStruct('ProductVersion', '{__version__}'),
        StringStruct('LegalCopyright', '(c) {DEV_NAME}'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0412, 0x04B0])])
  ]
)
"""
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)
    return path


def _common_args() -> list[str]:
    args = [
        SRC,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--name", APP_NAME,
        "--paths", ROOT,
        "--version-file", _write_version_file(),
        # QML 리소스 번들 (런타임에 _MEIPASS/gui/qml 로 로드)
        "--add-data", f"{QML_DIR}{SEP}gui/qml",
        # QML 앱은 Python에서 QtQuick를 직접 import 하지 않으므로 명시적으로 포함해
        # Qt Quick / Controls 플러그인이 누락되지 않게 한다.
        "--hidden-import", "PySide6.QtQml",
        "--hidden-import", "PySide6.QtQuick",
        "--hidden-import", "PySide6.QtQuickControls2",
        "--hidden-import", "PySide6.QtNetwork",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(ROOT, "build"),
        "--specpath", os.path.join(ROOT, "build"),
    ]
    if os.path.exists(ICON):
        args += ["--icon", ICON]
    return args


def build_full() -> None:
    ffmpeg = os.path.join(ROOT, "bin", "ffmpeg.exe")
    ffprobe = os.path.join(ROOT, "bin", "ffprobe.exe")
    if not os.path.exists(ffmpeg):
        raise SystemExit(f"[full] ffmpeg 없음: {ffmpeg}  (bin/ffmpeg.exe 배치 필요)")

    args = _common_args() + [
        "--onedir",
        "--add-binary", f"{ffmpeg}{SEP}ffmpeg",
    ]
    if os.path.exists(ffprobe):
        args += ["--add-binary", f"{ffprobe}{SEP}ffmpeg"]
    print(">>> [full] 폴더형 + ffmpeg 번들 빌드 시작")
    PyInstaller.__main__.run(args)
    print(">>> [full] 완료 -> dist/%s/" % APP_NAME)


def build_lite() -> None:
    # onefile 은 --name 이 exe 이름이 되므로 LITE_NAME 으로 덮어쓴다.
    args = [a for a in _common_args()]
    args[args.index(APP_NAME)] = LITE_NAME
    args += ["--onefile"]
    print(">>> [lite] 단일파일(ffmpeg 미포함) 빌드 시작")
    PyInstaller.__main__.run(args)
    print(">>> [lite] 완료 -> dist/%s.exe" % LITE_NAME)


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("full", "all"):
        build_full()
    if target in ("lite", "all"):
        build_lite()
    if target not in ("full", "lite", "all"):
        raise SystemExit("사용법: python build.py [full|lite|all]")


if __name__ == "__main__":
    main()
