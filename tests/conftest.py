"""pytest 공통 설정 · 픽스처.

- GUI 테스트는 화면 없이 돌도록 QT_QPA_PLATFORM=offscreen 강제.
- ffmpeg 미설치 환경에서는 통합 테스트를 자동 skip.
"""
import os
import subprocess
import sys
from pathlib import Path

# PySide6 임포트 전에 오프스크린 플랫폼 지정 (헤드리스 CI에서도 QML 로드 가능)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

# 프로젝트 루트를 경로에 추가 (pytest.ini pythonpath 백업)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ffmpeg_tools import FFmpegNotFound, find_tools  # noqa: E402


def _tools_or_none():
    try:
        return find_tools()
    except FFmpegNotFound:
        return None


@pytest.fixture(scope="session")
def tools():
    """ffmpeg/ffprobe. 없으면 해당 테스트 skip."""
    t = _tools_or_none()
    if t is None or not t.ffprobe:
        pytest.skip("ffmpeg/ffprobe 미설치 — 통합 테스트 skip")
    return t


@pytest.fixture(scope="session")
def sample_mp4(tmp_path_factory, tools):
    """3초짜리 파란 화면 + 440Hz 사인파 테스트 mp4 생성."""
    out = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run(
        [
            tools.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3",
            "-shortest", "-pix_fmt", "yuv420p", str(out),
        ],
        check=True, capture_output=True,
    )
    return out


@pytest.fixture(scope="session")
def soffice():
    """LibreOffice 경로. 없으면 해당 테스트 skip."""
    from core.document import SofficeNotFound, find_soffice
    try:
        return find_soffice()
    except SofficeNotFound:
        pytest.skip("LibreOffice 미설치 — 문서 변환 통합 테스트 skip")


@pytest.fixture(scope="session")
def qapp():
    """QML/워커 테스트용 QGuiApplication (세션당 하나). PySide6 없으면 skip."""
    pytest.importorskip("PySide6")
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


@pytest.fixture
def run_worker(qapp):
    """ConversionWorker를 이벤트 루프에서 동기적으로 돌리고 결과 dict 반환."""
    from PySide6.QtCore import QEventLoop, QTimer

    def _run(worker, timeout_ms=60000):
        loop = QEventLoop()
        result = {}
        worker.finished.connect(
            lambda ok, msg: (result.update(ok=ok, msg=msg), loop.quit())
        )
        QTimer.singleShot(0, worker.run)
        guard = QTimer()
        guard.setSingleShot(True)
        guard.timeout.connect(lambda: (result.setdefault("timeout", True), loop.quit()))
        guard.start(timeout_ms)
        loop.exec()
        return result

    return _run


def _probe_stream(ffprobe: str, path) -> dict:
    """출력 오디오 스트림 정보(codec/sample_rate/channels/duration) 조회 — 검증용."""
    out = subprocess.run(
        [
            ffprobe, "-v", "error",
            "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
            "-of", "default=noprint_wrappers=1", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    info = {}
    for line in out.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            info[k] = v
    return info


@pytest.fixture
def probe():
    """출력 미디어의 스트림 정보를 조회하는 헬퍼 함수를 반환."""
    return _probe_stream
