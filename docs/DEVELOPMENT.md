# FormatConverter — 개발 문서

> 이 문서는 작업을 **언제든 중단하고 재개**할 수 있도록 프로젝트의 목표·구조·진행 상황·다음 할 일을 기록한다.
> 새 세션을 시작할 때 이 문서를 먼저 읽으면 현재 상태를 파악할 수 있다.

- 최종 수정: 2026-07-07
- 저장소 경로: `F:\Git\FormatConverter`

---

## 1. 프로젝트 개요

온라인 변환 서비스(CloudConvert, Convertio)를 대체하는 **로컬 파일 포맷 컨버터**.
파일을 외부 클라우드에 올리지 않고, 광고 없이 내 PC에서 직접 변환한다. (핵심: mp4 → mp3)

### 핵심 요구사항
| # | 요구사항 | 상태 |
|---|----------|------|
| 1 | 드래그앤드롭으로 파일 추가 | ✅ 구현 |
| 2 | 입력 종류에 따라 가능한 출력 포맷 자동 노출 | ✅ 구현 |
| 3 | **영상 → 음원** 변환 (C2: mp4→mp3 등) | ✅ 구현 |
| 4 | 음원 → 음원 변환 (C3) | ✅ 구현 |
| 5 | 고급 옵션(비트레이트·샘플레이트·채널·볼륨·정규화·구간자르기) | ✅ 구현 |
| 6 | **UI 멈춤 없는** 백그라운드 변환 + 진행률 | ✅ 구현 (QThread) |
| 7 | 여러 파일 일괄 변환 + 취소 | ✅ 구현 |
| 8 | 배포용 단독 실행 exe (full/lite 2종) | ✅ 구현 (`build.py`) |
| 9 | 버전 태그 기반 GitHub Release 자동 배포 | ✅ 구현 (GitHub Actions) |
| 10 | 영상 → 영상 변환 (C1) | ⏳ 2차 |
| 11 | 이미지 → 이미지 변환 (C4, Pillow) | ⏳ 2차 |
| 12 | 영상 ↔ 이미지 (C5/C6), 문서 변환 | ⏳ 이후 |

---

## 2. 기술 스택 (결정 사항)

| 구분 | 선택 | 이유 |
|------|------|------|
| 언어 | **Python 3.11+** (개발 PC는 3.14) | 변환 엔진을 조립하는 역할, 무거운 연산은 외부 도구가 담당 |
| GUI | **PySide6 + QML(Qt Quick)** | GPU 가속 렌더링으로 부드러운 UI, LGPL(상업적 무료), 성숙한 스레딩 |
| 미디어 변환 | **ffmpeg** | 영상/음원 변환 표준 (외부 바이너리) |
| 이미지 변환 | **Pillow** | 순수 파이썬, 번들 간단 (2차 카테고리 C4) |
| 배포 | **PyInstaller** | 단독 실행 exe (ffmpeg 번들 포함) |

### UI 형태 / 배포 방식 (사용자 확정)
- UI: **데스크톱 GUI** — 드래그앤드롭, 웹풍의 부드러운 렌더링
- 배포: **배포용 exe** (full: ffmpeg 포함 / lite: 미포함)

> "UI가 뚝뚝 끊기지 않게" 가 핵심 요구 → 변환은 **반드시 UI 스레드 밖(QThread)** 에서 실행.

---

## 3. 프로젝트 구조

```
FormatConverter/
├── docs/
│   ├── DESIGN.md              # 포맷·카테고리·옵션 설계 (예시 페이지 기능 대응)
│   ├── DEVELOPMENT.md         # (이 문서) 개발 진행/재개용 기록
│   ├── lite-ffmpeg-안내.md    # lite 배포 동봉용 ffmpeg 준비 안내
│   └── release_body_template.md  # GitHub Release 본문 템플릿
├── core/                      # 변환 로직 (UI 독립 — 단독 테스트 가능)
│   ├── registry.py            # 포맷/카테고리/라우팅 데이터 정의
│   ├── ffmpeg_tools.py        # ffmpeg/ffprobe 탐색 + 길이 조회
│   └── media.py               # FFmpeg 오디오 변환 명령 생성
├── gui/                       # PySide6 + QML UI
│   ├── backend.py             # QML↔Python 브리지 (QObject)
│   ├── worker.py              # QThread 백그라운드 변환 워커
│   └── qml/main.qml           # 드래그앤드롭 UI + 고급옵션 + 진행률
├── bin/                       # ffmpeg.exe/ffprobe.exe (직접 배치, git 제외)
├── .github/workflows/release.yml  # 태그 push → 빌드 → Release 자동화
├── build.py                   # PyInstaller 빌드 (full/lite)
├── version.py                 # 버전 단일 소스
├── main.py                    # 진입점
├── requirements.txt
└── README.md
```

### 모듈 책임 분리
- **core/** — UI와 완전 분리. `python -c "from core...."` 로 단독 테스트 가능.
  - `registry.py`: `MediaKind`, `Format`, `FORMATS`(확장자→종류), `IMPLEMENTED_ROUTES`,
    `output_formats_for(ext)`, `is_supported_input(ext)`, `kind_of(ext)`.
    → **새 포맷/경로 추가 시 이 데이터만 늘리면 된다.**
  - `ffmpeg_tools.py`: `find_tools() -> Tools(ffmpeg, ffprobe)`, `probe_duration()`.
    개발/번들(full)/단일exe(lite)/PATH 순으로 탐색(`_candidate_dirs`).
  - `media.py`: `AudioOptions` 데이터클래스, `build_audio_command()`, `segment_duration()`,
    `AUDIO_CODECS`(출력 확장자→코덱·손실여부).
- **gui/** — UI만 담당. 무거운 변환은 **QThread** 에서 실행.
  - `backend.py` `Backend(QObject)`: `files`/`outputFormats`/`progress`/`status`/`busy` 프로퍼티,
    `addUrls`/`clearFiles`/`setOutputFormat`/`start`/`cancel` 슬롯. 옵션 dict→`AudioOptions` 변환.
  - `worker.py` `ConversionWorker(QObject)`: `run()`에서 파일별 순차 변환, ffmpeg `-progress`
    파이프 파싱으로 진행률 계산, `progress`/`status`/`finished` 시그널.
  - `qml/main.qml`: DropArea + 파일 리스트 + 출력포맷 ComboBox + 고급옵션 GroupBox + 진행바.

---

## 4. 동작 흐름

```
[파일 드래그앤드롭] → (확장자로 종류 판별·필터) → 파일 목록에 추가
        │                                              │
        │                          입력 종류에 맞는 출력 포맷 자동 노출
        ▼                                              ▼
[출력 포맷 선택] → [고급 옵션 조절(선택)] → [변환 시작]
                                              │
                          QThread에서 파일별 ffmpeg 순차 실행
                          + -progress 파이프로 진행률 갱신(UI 안 멈춤)
```

- 영상 입력 → 음원 출력 목록(mp3/aac/wav/flac/…) 노출.
- 고급 옵션: 비트레이트, 샘플레이트(원본/44100/48000/22050), 채널(원본/스테레오/모노),
  볼륨(dB), 정규화(loudnorm), 구간 자르기(시작~끝 초).
- 진행률: `(완료 파일 수 + 현재 파일 진행분) / 전체`.

### FFmpeg 명령 매핑 (docs/DESIGN.md §8, §9)
- 구간 자르기: `-ss`(시작)/`-to`(끝) 를 **입력 옵션**으로 배치(입력 파일 절대 타임스탬프 기준).
- 음원 출력: `-vn` 으로 영상 제거, `-c:a` 코덱, 손실 코덱만 `-b:a`/`-q:a`.
- 필터 체인(`-af`): `volume`, `loudnorm`, `afade`(in/out).

---

## 5. 개발 환경 세팅

```powershell
# 1) 가상환경 (권장). PySide6 휠 문제 시 Python 3.12/3.13 사용 검토.
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) 의존성 설치
pip install -r requirements.txt

# 3) ffmpeg 준비 (둘 중 하나)
#   a. 시스템 PATH에 설치       (winget install Gyan.FFmpeg)
#   b. bin/ffmpeg.exe, bin/ffprobe.exe 배치  → 자동 인식 (bin/README.md 참고)

# 4) 실행
python main.py
```

> 개발 PC는 **Python 3.14 + PySide6 6.11** 로 동작 확인됨.
> ffmpeg는 gyan.dev full build로 mp4→mp3 end-to-end 검증 완료.

---

## 6. 배포 (exe 빌드) — ✅ 구현 (`build.py`)

| 산출물 | 명령 | 방식 | ffmpeg | 결과물 |
|--------|------|------|--------|--------|
| **full (기본)** | `python build.py full` | 폴더형(onedir) | **포함** | `dist/FormatConverter/` |
| **lite (라이트)** | `python build.py lite` | 단일파일(onefile) | 미포함 | `dist/FormatConverter-lite.exe` |

```powershell
pip install pyinstaller
python build.py           # full + lite 모두
```

- 공통: `--windowed`, `--add-data gui/qml`, QtQuick/Controls 히든임포트, `--paths .`, 버전 리소스.
- full: `bin/ffmpeg.exe`, `bin/ffprobe.exe`를 `ffmpeg/` 하위로 번들 → 런타임 자동 인식.
- 아이콘: `assets/app.ico`가 있으면 자동 적용.
- exe 버전 리소스에 개발자명(`DEV_NAME`) 메타데이터 포함.

### ffmpeg 탐색 순서 (`core/ffmpeg_tools.py._candidate_dirs`)
1. **번들(full)**: `sys._MEIPASS/ffmpeg/ffmpeg.exe`
2. **실행파일 옆(lite)**: `<exe>/ffmpeg.exe`, `<exe>/ffmpeg/`, `<exe>/bin/`
3. **개발 환경**: 프로젝트 `bin/ffmpeg.exe`
4. 위 모두 없으면 **시스템 PATH**

### 배포 방법
- **full**: `dist/FormatConverter/` 폴더 전체를 zip으로 전달 → 압축 풀고 `FormatConverter.exe` 실행.
- **lite**: `FormatConverter-lite.exe` 단일 파일. ffmpeg 미포함 → `docs/lite-ffmpeg-안내.md` 동봉.

---

## 6-1. 릴리스 / 버전 태그 자동 배포

버전은 `version.py`의 `__version__`이 단일 소스이며, 창 제목에 `v{버전}`으로 표시된다.
릴리스는 **Git 태그 push**로 트리거된다 — `.github/workflows/release.yml`(GitHub Actions).

```powershell
git tag -a v1.0.0 -m "변경 내용 요약"
git push origin v1.0.0     # -> Actions가 자동 빌드 & Release 발행
```

### 워크플로 동작 (windows-latest)
1. Python 3.12 + 의존성/PyInstaller 설치
2. 태그명에서 버전 추출해 `version.py`에 기록(산출물에만 반영, 커밋 안 함)
3. ffmpeg(essentials) 다운로드 → `bin/`에 배치 (CI에는 ffmpeg가 없으므로)
4. `python build.py all` 로 full + lite 빌드
5. zip 패키징: `FormatConverter-full-<버전>.zip`, `FormatConverter-lite-<버전>.zip`(+안내문)
6. `softprops/action-gh-release`로 Release 생성 + zip 첨부

> 릴리스 노트의 "이번 버전 변경사항"은 **주석 태그 메시지**(`git tag -a -m`)에서 추출된다
> (`docs/release_body_template.md`의 `{{CHANGES}}`에 주입).

---

## 6-2. 자동 테스트 / 브랜치 전략

- 테스트는 **pytest** 3계층(① 단위 · ② GUI 스모크 · ③ 실제 ffmpeg 통합). 상세는 `docs/TEST.md`.
- 기능 추가·수정·버그 수정 때마다 **`pytest` 전체 회귀**로 검증한다. (현재 37개, ~1초)
- CI: `.github/workflows/test.yml` 이 dev/main push·PR 에서 전체 테스트 실행.
  릴리스(`release.yml`)는 **테스트 통과 후에만**(`needs: test`) 빌드 → 깨진 채 배포 방지.

### 브랜치 전략
- 개발은 **`dev` 브랜치**에서 진행. push 시 `test.yml` 이 자동 검증.
- 배포할 때만 **`main` 에 머지**하고, `main` 에서 `git tag -a vX.Y.Z` push → 릴리스.

---

## 6-3. 자동 업데이트 (`core/updater.py` + `gui/update_checker.py`)

- 실행 1.5초 후 백그라운드 스레드로 GitHub `releases/latest` 조회(**패키지 빌드만**, dev는 skip.
  `FORMATCONVERTER_FORCE_UPDATE=1` 로 dev에서도 강제 확인 가능).
- 최신 태그가 현재 `__version__` 보다 높으면 QML 다이얼로그 표시:
  새 버전 · 현재 버전 · 변경요약 · [나중에]/[지금 업데이트].
- **[지금 업데이트]**: 빌드 종류(full/lite)에 맞는 zip을 받아 도우미 PowerShell 스크립트를
  숨김 실행하고 앱 종료. 스크립트가 프로세스 종료를 기다렸다가 파일 교체 후 재시작.
  - `lite`: 실행 중 exe는 못 덮어쓰므로 **rename 후 새 파일 복사**(부트로더 잠금 회피).
  - `full`: 프로세스 종료 후 폴더 덮어쓰기(`Copy-Item -Recurse -Force`).
  - 진단 로그: `%TEMP%/FormatConverter_update.log`. 비ASCII 경로 대응 위해 UTF-8 BOM + `-LiteralPath`.
- 변경요약: 릴리스 본문 `<!--CHANGES-->…<!--/CHANGES-->`(= 태그 메시지)에서 추출.
- 빌드 종류 판별: frozen + `_internal` 폴더 → full, frozen → lite, 비프리즈 → dev.

> 주의: 자동 업데이트는 **이 기능이 포함된 버전부터** 동작(예: v0.0.2에 처음 탑재 시,
> v0.0.2 사용자가 v0.0.3부터 알림을 받음).

---

## 7. 진행 상황 / TODO

### 완료
- [x] 기술 스택 결정(PySide6+QML) 및 설계 문서화(`docs/DESIGN.md`)
- [x] `core/registry.py` — 포맷/카테고리/라우팅 데이터 정의(C1~C4 설계)
- [x] `core/media.py` — FFmpeg 오디오 변환 명령 생성(고급옵션 대응)
- [x] `core/ffmpeg_tools.py` — ffmpeg/ffprobe 탐색 + 길이 조회
- [x] `gui/backend.py` + `gui/worker.py` — QThread 백그라운드 변환 + 진행률
- [x] `gui/qml/main.qml` — 드래그앤드롭 UI + 고급옵션 펼침 + 진행바
- [x] **mp4→mp3 end-to-end 변환 검증**(구간자르기·샘플레이트·채널·정규화 적용)
- [x] QML 로드 / 드래그앤드롭 필터링 / 옵션 변환 검증
- [x] 배포 인프라: `build.py`(full/lite), `version.py`, GitHub Actions 릴리스 워크플로
- [x] 배포 문서: `DEVELOPMENT.md`, `lite-ffmpeg-안내.md`, `release_body_template.md`
- [x] **full/lite exe 실제 빌드·기동 검증** (offscreen 스모크 통과. full 824MB / lite 168MB)
- [x] 자동 테스트 파이프라인: pytest 3계층, `test.yml`(dev/main) + 릴리스 게이트(`needs: test`)
- [x] 브랜치 전략 확정: dev 개발 / main 배포
- [x] 첫 릴리스 `v0.0.1` 배포(full/lite zip 자산 발행 확인)
- [x] 자동 업데이트(`core/updater.py` + `gui/update_checker.py` + QML 다이얼로그): 실행 시
  최신 릴리스 확인 → 변경요약 모달 → full/lite 자동 교체·재시작. 순수 로직 단위 테스트 포함

### 다음 할 일 (우선순위 순)
- [ ] **배포 용량 축소**: PySide6 불필요 Qt 모듈 exclude(`--exclude-module`)로 824MB 감량
- [ ] C1 영상→영상 변환 엔진 추가 (`media.py`에 VideoOptions/명령 생성, ROUTES 확장)
- [ ] C3 음원→음원 UI 노출 정리(현재 엔진은 지원, 입력 필터만 확장)
- [ ] C4 이미지→이미지 변환(`core/image.py` Pillow 엔진) + registry 라우팅
- [ ] 출력 폴더 선택 UI(현재는 입력 파일과 같은 폴더에 저장)
- [ ] 변환 완료 후 폴더 열기 / 개별 파일 진행률 표시
- [ ] 예외 메시지 한글화(코덱 미지원·손상 파일 등), 앱 아이콘(`assets/app.ico`)

### 알려진 제약 / 메모
- Python 3.14는 최신 → 일부 패키지 휠 미제공 가능성. 문제 시 3.12/3.13 사용.
- PyInstaller + QML은 Qt Quick 플러그인 누락에 주의 → `build.py`에 히든임포트로 대응.
  런타임에 QML 모듈 누락 오류가 나면 `--collect-all PySide6` 로 강제 수집 검토.
- 손실 코덱만 비트레이트 적용, 무손실(wav/flac/aiff)은 비트레이트 옵션 무시.
- 페이드 아웃은 변환 구간 길이(`segment_duration`)를 알아야 정확 → ffprobe 필요.

---

## 8. 재개 체크리스트 (새 세션 시작 시)
1. 이 문서 §7 "다음 할 일" 확인
2. `pip install -r requirements.txt` 상태 확인
3. ffmpeg 사용 가능 여부 확인 (`bin/ffmpeg.exe` 또는 PATH)
4. `python main.py`로 현재 동작 확인 후 이어서 작업
