# FormatConverter

로컬에서 동작하는 파일 포맷 변환기입니다.
**클라우드 업로드나 광고 없이** 내 PC에서 파일을 변환하기 위해 만들었습니다.

> 파일이 외부로 전송되지 않으므로 개인정보·보안에 안전하고, 네트워크 없이도 변환됩니다.

## 주요 기능
- 🎬 **영상 → 음원** 변환 (mp4 → mp3 등) — *1차 릴리즈*
- 🖱️ **드래그앤드롭** 으로 파일 추가
- ⚙️ **고급 옵션**: 비트레이트 · 샘플레이트 · 채널 · 볼륨/정규화 · 구간 자르기 · 페이드
- 📊 변환 **진행률 표시**, UI 멈춤 없음(백그라운드 처리)
- 🎯 목표: 온라인 변환 서비스가 제공하는 변환 기능을 로컬에서 전부 대응

## 지원 예정 변환 카테고리
| 그룹 | 변환 | 예시 | 릴리즈 |
|------|------|------|--------|
| C2 | 영상 → 음원 | mp4 → mp3, mkv → aac | **1차** |
| C1 | 영상 → 영상 | mp4 → mkv, avi → mp4 | 2차 |
| C3 | 음원 → 음원 | wav → mp3, flac → aac | 2차 |
| C4 | 이미지 → 이미지 | png → jpg, heic → jpg | 2차 |
| C5/C6 | 영상 ↔ 이미지 | mp4 → gif, png 시퀀스 → mp4 | 이후 |

자세한 내용은 [`docs/DESIGN.md`](docs/DESIGN.md) 참고.

## 기술 스택
- **언어**: Python 3.11+
- **UI**: PySide6 + QML (Qt Quick) — GPU 가속, 부드러운 렌더링
- **변환 엔진**: FFmpeg(미디어), Pillow(이미지)
- **배포**: PyInstaller 단일 `.exe`

## 요구 사항
- Python 3.11 이상
- [FFmpeg](https://ffmpeg.org/) (실행 파일을 `bin/`에 두거나 시스템 PATH에 등록)

## 설치 및 실행
```powershell
# 가상환경 생성 (PySide6 휠 문제 시 Python 3.12/3.13 권장)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt
# ffmpeg 필요: winget install Gyan.FFmpeg  (또는 bin/ 폴더에 ffmpeg.exe·ffprobe.exe 배치)

# 실행
python main.py
```

## 배포용 exe 빌드
```powershell
pip install pyinstaller
python build.py          # full(폴더형+ffmpeg) + lite(단일파일) 모두 빌드
```
- **full**: `dist/FormatConverter/` — ffmpeg 포함, 폴더째 zip으로 배포
- **lite**: `dist/FormatConverter-lite.exe` — 단일 파일, ffmpeg 미포함
  ([`docs/lite-ffmpeg-안내.md`](docs/lite-ffmpeg-안내.md) 동봉)

**macOS** (`python build.py` → `dist/FormatConverter.app`, Apple Silicon/arm64):
```bash
python build.py            # OS 자동 분기 → .app 생성
brew install ffmpeg        # 변환 엔진(앱에 미포함, 자동 탐색)
```
서명 없이 배포하므로 최초 실행은 우클릭→열기 ([`docs/macos-안내.md`](docs/macos-안내.md) 참고).

### 릴리스 (자동 배포)
버전 태그를 push하면 GitHub Actions가 exe를 빌드해 Release로 배포합니다.
```powershell
git tag -a v1.0.0 -m "변경 내용 요약"
git push origin v1.0.0
```

자세한 개발 정보와 진행 상황은 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) 참고.

## 프로젝트 구조
```
FormatConverter/
├─ core/            # 변환 로직 (UI 독립)
│  ├─ registry.py   # 포맷/카테고리/엔진 라우팅 정의
│  ├─ media.py      # FFmpeg 래퍼
│  └─ image.py      # Pillow 래퍼
├─ gui/
│  ├─ qml/          # QML UI
│  ├─ main_window.py
│  └─ worker.py     # QThread 변환 워커
├─ bin/             # ffmpeg.exe 번들 (git 제외)
├─ docs/
│  └─ DESIGN.md     # 설계 문서
└─ main.py
```

## 라이선스
- 애플리케이션 코드: MIT (예정)
- FFmpeg는 별도 라이선스(LGPL/GPL)를 따르며 번들 시 해당 고지를 포함합니다.
