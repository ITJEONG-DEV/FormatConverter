# FormatConverter

로컬에서 동작하는 파일 포맷 변환기입니다.
**클라우드 업로드나 광고 없이** 내 PC에서 영상·음원·이미지·문서를 서로 변환합니다.

> 파일이 외부로 전송되지 않으므로 개인정보·보안에 안전하고, 네트워크 없이도 변환됩니다.

## 주요 기능
- 🔄 **폭넓은 변환**: 영상·음원·이미지·문서 상호 변환 + 이미지↔pdf (아래 표)
- 🖱️ **드래그앤드롭**으로 파일 추가, 여러 파일 **일괄 변환**
- 🗂️ **출력 종류 → 포맷 2단계 선택**: 입력에 맞는 종류(영상/음원/이미지/문서)만 노출
- ⚙️ **고급 옵션**: 비트레이트·샘플레이트·채널·볼륨/정규화·구간 자르기(음원), 해상도·fps·화질(영상),
  품질·해상도(이미지), 이미지당 시간·크기(슬라이드쇼)
- 📁 **저장 위치 선택** + 변환 후 **폴더 열기**
- 📊 **전체 + 현재 파일 진행률**, 오디오 출력은 **예상 크기** 표시, UI 멈춤 없음(백그라운드 처리)
- ↕️ 파일 목록 **순서 변경(▲/▼)·제거(✕)** — 이미지 시퀀스 순서에 사용
- 🔔 실행 시 **자동 업데이트** 확인(Windows), 실패 시 **한글 안내 메시지**

## 지원 변환
| 입력 → 출력 | 예시 | 엔진 |
|-------------|------|------|
| 영상 → 영상 (C1) | mp4 → mkv, avi → mp4 | FFmpeg |
| 영상 → 음원 (C2) | mp4 → mp3, mkv → aac | FFmpeg |
| 음원 → 음원 (C3) | wav → mp3, flac → aac | FFmpeg |
| 이미지 → 이미지 (C4) | png → jpg, heic → jpg | Pillow |
| 영상 → 이미지 (C5) | mp4 → gif/webp, 프레임 추출 | FFmpeg |
| 이미지 → 영상 (C6) | png 시퀀스 → mp4 (슬라이드쇼) | FFmpeg |
| 문서 → 문서 (C7) | docx → pdf, xlsx → pdf | LibreOffice |
| 이미지 → pdf (C8) | png/jpg → 다중 페이지 pdf | Pillow |
| pdf → 이미지 (C9) | pdf → png/jpg (페이지별) | pypdfium2 |

지원 확장자와 설계 세부는 [`docs/DESIGN.md`](docs/DESIGN.md), 개발 현황은 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) 참고.

## 기술 스택
- **언어**: Python 3.11+
- **UI**: PySide6 + QML (Qt Quick) — GPU 가속, 부드러운 렌더링
- **변환 엔진**: FFmpeg(영상·음원) · Pillow(이미지·이미지→pdf) · pypdfium2(pdf→이미지) · LibreOffice(문서)
- **배포**: PyInstaller (`.exe` / `.app`), GitHub Actions 자동 릴리스, 자동 업데이트

## 요구 사항
- Python 3.11 이상 (PySide6 휠 문제 시 3.12/3.13 권장)
- [FFmpeg](https://ffmpeg.org/) — 영상·음원 변환 (실행 파일을 `bin/`에 두거나 PATH에 등록)
- (선택) [LibreOffice](https://www.libreoffice.org/) — 문서 변환(docx/xlsx/pptx ↔ pdf 등) 시에만 필요
- pip 의존성(`requirements.txt`): PySide6, Pillow, pypdfium2

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

## 배포용 빌드
```powershell
pip install pyinstaller
python build.py          # (Windows) full + lite / (macOS) .app
```
- **full**: `dist/FormatConverter/` — ffmpeg 포함, 폴더째 zip으로 배포
- **lite**: `dist/FormatConverter-lite.exe` — 단일 파일, ffmpeg 미포함 ([`docs/lite-ffmpeg-안내.md`](docs/lite-ffmpeg-안내.md) 동봉)
- **macOS**: `dist/FormatConverter.app` (Apple Silicon 기본, Intel은 요청 시). `brew install ffmpeg` 연동,
  서명 없이 배포하므로 최초 실행은 우클릭→열기 ([`docs/macos-안내.md`](docs/macos-안내.md))

### 릴리스 (자동 배포)
버전 태그를 push하면 GitHub Actions가 테스트 통과 후 빌드해 Release로 배포합니다
(Windows full/lite + macOS arm64). Intel(x86_64)은 `macos-intel.yml`을 수동 실행해 추가합니다.
```powershell
git tag -a v1.0.0 -m "변경 내용 요약"
git push origin v1.0.0
```

## 테스트
```powershell
pip install -r requirements-dev.txt
pytest                                   # 전체 회귀 (외부 엔진 없으면 해당 테스트 자동 skip)
git config core.hooksPath .githooks      # push 전 자동 테스트 훅 활성화
```
자세한 내용은 [`docs/TEST.md`](docs/TEST.md).

## 프로젝트 구조
```
FormatConverter/
├─ core/                  # 변환 로직 (UI 독립)
│  ├─ registry.py         # 포맷/카테고리/경로 정의, 출력 필터
│  ├─ media.py            # FFmpeg 명령 생성 (영상·음원·영상→이미지)
│  ├─ image.py            # Pillow (이미지 변환·이미지→pdf)
│  ├─ pdf.py              # pypdfium2 (pdf→이미지)
│  ├─ document.py         # LibreOffice (문서 변환)
│  ├─ ffmpeg_tools.py     # ffmpeg/ffprobe 탐색·길이 조회
│  ├─ estimate.py         # 파일 크기·예상 출력 크기
│  ├─ errors.py           # 실패 메시지 한글화
│  └─ updater.py          # 자동 업데이트 순수 로직
├─ gui/
│  ├─ backend.py          # QML↔Python 브리지
│  ├─ worker.py           # QThread 변환 워커
│  ├─ update_checker.py   # 자동 업데이트 QML 브리지
│  └─ qml/main.qml        # UI
├─ assets/                # 아이콘(app.ico/icns/png) + 생성기
├─ tests/                 # pytest (단위·GUI·통합)
├─ docs/                  # DESIGN / DEVELOPMENT / TEST / 배포 안내
├─ .github/workflows/     # test / release / macos-intel(수동)
├─ .githooks/pre-push     # push 전 자동 테스트
├─ bin/                   # ffmpeg 실행 파일 (git 제외)
├─ build.py               # PyInstaller 빌드
├─ version.py             # 버전 단일 소스
└─ main.py                # 진입점
```

## 라이선스
- 애플리케이션 코드: MIT (예정)
- 외부 엔진은 각자의 라이선스를 따릅니다: FFmpeg(LGPL/GPL), Pillow(HPND/MIT-CMU),
  pypdfium2·pdfium(BSD/Apache), LibreOffice(MPL/별도 설치). 번들 시 해당 고지를 포함합니다.
