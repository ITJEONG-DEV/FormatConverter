# 자동 테스트 가이드 (TEST.md)

FormatConverter 의 자동 테스트 구조 · 실행 방법 · 규칙을 정리한 문서.
**기능을 추가하거나 수정할 때마다 전체 테스트를 돌려 회귀(regression)를 확인**하는 것이 목표.

---

## 1. 한눈에

| 계층 | 대상 | 마커 | 기본 실행 | 특징 |
|------|------|------|:--------:|------|
| ① 단위 | 순수 로직 (registry / media 명령 생성) | 없음 | ✅ | ffmpeg·GUI 없이 매우 빠름 |
| ② GUI 스모크 | QML 로드 + Backend (offscreen) | `gui` | ✅ | 화면 없이 검증, PySide6 없으면 skip |
| ③ 통합 | 실제 ffmpeg 변환 | `ffmpeg` | ✅ | 실제 mp4→mp3 변환·ffprobe 검증, ffmpeg 없으면 skip |

- 테스트 러너: **pytest** (`requirements-dev.txt`)
- 설정: 루트 `pyproject.toml` 의 `[tool.pytest.ini_options]`
- 외부 의존(ffmpeg/PySide6)이 없으면 **실패가 아니라 자동 skip** 되어, 어떤 환경에서도 안전하게 돌아간다.
- 현재 **37개 테스트** (단위 22 · GUI 6 · 통합 9), 약 1초.

---

## 2. 실행 방법

```powershell
# 준비(최초 1회)
pip install -r requirements.txt -r requirements-dev.txt
# ffmpeg 준비: winget install Gyan.FFmpeg  또는 bin/ 에 ffmpeg.exe·ffprobe.exe 배치
git config core.hooksPath .githooks    # push 전 자동 테스트 훅 활성화(§6)

# 전체 회귀 — 기능 추가/수정 후 항상 이걸 실행
pytest

# 커버리지 포함
pytest --cov=core --cov=gui --cov-report=term-missing

# 단위 테스트만 (가장 빠름, ffmpeg·GUI 불필요)
pytest -m "not gui and not ffmpeg"

# GUI 스모크만 / 통합만
pytest -m gui
pytest -m ffmpeg

# 특정 파일/테스트
pytest tests/test_media.py
pytest tests/test_media.py::test_trim_placed_before_input
```

> Windows에서 `pytest` 명령이 안 잡히면 `python -m pytest` 로 실행.
> GUI 테스트는 `conftest.py` 가 `QT_QPA_PLATFORM=offscreen` 을 지정해 창 없이 돈다.

---

## 3. 폴더 구조

```
pyproject.toml            # pytest 설정(마커, pythonpath=".")
requirements-dev.txt      # pytest 등 개발 전용 의존성
tests/
├── conftest.py           # 공용 픽스처: tools, sample_mp4, qapp, run_worker, probe
├── test_registry.py      # ① 포맷/카테고리 라우팅
├── test_media.py         # ① FFmpeg 명령 생성(코덱·비트레이트·구간·필터·VBR)
├── test_ffmpeg_tools.py  # ① 탐색 실패/PATH  + ③ probe_duration
├── test_conversion.py    # ③ 실제 mp4→mp3/wav 변환 + 워커 파이프라인(단일/다중)
└── test_gui.py           # ② QML 로드 + Backend 필터/출력포맷/옵션변환
```

### 공용 픽스처 (conftest.py)
- **`tools`** — `find_tools()` 결과(ffmpeg/ffprobe). 없으면 skip.
- **`sample_mp4`** — 3초짜리 테스트 mp4를 ffmpeg로 생성(세션 1회).
- **`qapp`** — offscreen `QGuiApplication`(세션 1개). PySide6 없으면 skip.
- **`run_worker`** — `ConversionWorker`를 이벤트 루프에서 동기 실행하고 결과 dict 반환.
- **`probe`** — 출력 파일의 codec/sample_rate/channels/duration 조회 헬퍼.

---

## 4. 테스트 작성 규칙

- **① 단위는 subprocess를 실제 실행하지 않는다.** `build_audio_command`가 만든 인자 리스트만 검증(빠름).
- **외부 의존은 마커로 격리.** ffmpeg가 필요하면 `@pytest.mark.ffmpeg` + `tools` 픽스처,
  GUI가 필요하면 `@pytest.mark.gui` + `qapp` 픽스처를 쓴다 → 없는 환경에서 자동 skip.
- **파일 오염 금지.** 변환 출력은 항상 `tmp_path`(pytest 임시 폴더)에 쓴다.
- **QGuiApplication은 세션당 1개.** 여러 번 생성하면 불안정 → `qapp` 픽스처를 공유한다.
- **비동기(QThread) 검증은 `run_worker`** 로 실제 이벤트 루프를 돌려 `finished` 시그널을 기다린다.
- 새 코덱/포맷/옵션을 추가하면 `test_media.py`(명령 생성)와 `test_conversion.py`(실제 변환)에 함께 추가.

---

## 5. CI 연동 (GitHub Actions)

| 워크플로 | 트리거 | 동작 |
|----------|--------|------|
| `.github/workflows/test.yml` | **dev/main push·PR** | ffmpeg 설치 후 `pytest` 전체 실행 |
| `.github/workflows/release.yml` | `v*` 태그 push | **`test` 잡 통과 후에만** 빌드/릴리스 (`needs: test`) |

- 두 워크플로 모두 `windows-latest` + `QT_QPA_PLATFORM=offscreen` 로 GUI 스모크까지 실행.
- CI는 ffmpeg(essentials)를 내려받아 `bin/`에 배치하므로 **통합 테스트까지 전부 수행**된다.
- `test.yml` 은 커버리지(`--cov`)도 리포트한다.
- **배포 게이트**: 테스트가 깨지면 릴리스 빌드가 자동 중단되어, 깨진 채 배포되는 것을 막는다.

### 브랜치 전략
- 개발은 **`dev` 브랜치**에서 진행 → push 시 `test.yml` 이 자동 검증.
- 배포할 때만 **`main` 에 머지**하고, `main` 에서 버전 태그(`vX.Y.Z`)를 push → 릴리스.

---

## 6. 로컬 자동화 (pre-push 훅)

원격에 올리기 전에 로컬에서도 자동으로 회귀를 막는다. 버전 관리되는 `.githooks/pre-push` 가
**push 직전 전체 `pytest` 를 실행**하고, 실패하면 push를 중단한다.

```powershell
git config core.hooksPath .githooks   # 최초 1회(클론마다) 활성화
```

- 이후 `git push` 하면 자동으로 테스트가 돌고, 통과해야 실제 push 된다.
- pytest/파이썬이 없으면 조용히 건너뛴다(기여자 환경 배려).
- 꼭 우회해야 하면 `git push --no-verify`.
- CI(`test.yml`)와 **이중 안전망**: 로컬에서 먼저 걸러 CI 낭비를 줄이고, CI가 최종 확인.

---

## 7. 새 기능을 추가/수정했다면 (체크리스트)

1. 해당 로직에 **단위 테스트**를 추가(가능하면 순수 함수로 분리해 ①에서 검증).
2. 실제 변환 경로가 바뀌었으면 `test_conversion.py` 에 **통합 테스트** 추가.
3. UI 흐름이 바뀌었으면 `test_gui.py` 에 **스모크 테스트** 추가.
4. 로컬에서 **`pytest`** 로 전체 회귀 초록불 확인.
5. `dev` 에 push → pre-push 훅 + `test.yml` 이 자동 재확인.
6. 배포 시 `main` 머지 후 태그 push → 테스트 통과해야 릴리스 진행.

---

## 8. 현재 커버리지 요약

- **registry**: `kind_of`, `is_supported_input`, `output_formats_for`(영상/음원/미지원).
- **media**: 코덱 선택(8종), 기본 비트레이트, 무손실 비트레이트 생략, 구간(`-ss/-to`) 입력측 배치,
  샘플레이트·채널, 필터(volume/loudnorm/fade-out), VBR override, 진행률 파이프, `segment_duration`.
- **ffmpeg_tools**: 탐색 실패(FFmpegNotFound), PATH 폴백, `probe_duration`(정상/잘못된 경로).
- **conversion(통합)**: mp3(44100·2ch) / wav(무손실) 변환, 구간 자르기 길이, 워커 단일·다중 파이프라인.
- **gui(스모크)**: QML 로드, 미지원 확장자 필터, 출력 포맷 노출, 목록 비우기, 옵션 dict→AudioOptions.
