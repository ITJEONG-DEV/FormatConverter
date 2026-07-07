# FormatConverter

로컬에서 동작하는 파일 포맷 변환기입니다. CloudConvert · Convertio 같은 온라인 변환 서비스를
**클라우드 업로드 없이, 광고 없이** 내 PC에서 그대로 쓰기 위해 만들었습니다.

> 파일이 외부로 전송되지 않으므로 개인정보·보안에 안전하고, 네트워크 없이도 변환됩니다.

## 주요 기능
- 🎬 **영상 → 음원** 변환 (mp4 → mp3 등) — *1차 릴리즈*
- 🖱️ **드래그앤드롭** 으로 파일 추가
- ⚙️ **고급 옵션**: 비트레이트 · 샘플레이트 · 채널 · 볼륨/정규화 · 구간 자르기 · 페이드
- 📊 변환 **진행률 표시**, UI 멈춤 없음(백그라운드 처리)
- 🎯 목표: 예시 페이지(CloudConvert/Convertio)가 지원하는 변환 기능 전부 대응

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
```bash
# 가상환경 생성
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
```

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
