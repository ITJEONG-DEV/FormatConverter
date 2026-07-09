# FormatConverter 설계 문서

> 구현된 현재 상태 기준(C1~C9). 진행 현황은 `docs/DEVELOPMENT.md`, 테스트는 `docs/TEST.md`.

## 1. 개요
- **목적**: 온라인 변환 서비스 대체용 **로컬** 파일 포맷 컨버터(클라우드 업로드·광고 없음)
- **기술 스택**: Python 3.11+ / PySide6 + QML(Qt Quick) / FFmpeg · Pillow · pypdfium2 · LibreOffice
- **UI**: 드래그앤드롭, 출력 종류→포맷 2단계 선택, 진행률 표시, UI 멈춤 없음(QThread)
- **배포**: PyInstaller (`.exe` full/lite, macOS `.app`), GitHub Actions 자동 릴리스 + 자동 업데이트

---

## 2. 변환 엔진 매핑
| 변환 | 엔진 | 비고 |
|------|------|------|
| 영상·음원 (C1·C2·C3·C5·C6) | **FFmpeg** (`subprocess`) | 명령 생성은 `core/media.py` |
| 이미지→이미지 (C4), 이미지→pdf (C8) | **Pillow** | `core/image.py`, 인프로세스 |
| pdf→이미지 (C9) | **pypdfium2** | `core/pdf.py`, BSD/Apache(배포 안전) |
| 문서→문서 (C7) | **LibreOffice** headless | `core/document.py`, 외부 설치 필요 |

엔진은 입력·출력 종류로 워커(`gui/worker.py`)가 분기하고, FFmpeg 명령은 `build_command`가 라우팅한다.

---

## 3. 지원 포맷
- **영상**: mp4, avi, mkv, mov, webm, flv, wmv, m4v, mpeg, ts, 3gp
- **음원**: mp3, wav, aac, flac, ogg, m4a, wma, opus, aiff
- **이미지**: png, jpg, jpeg, webp, bmp, gif, tiff, ico, heic
- **문서**: pdf, docx, doc, odt, rtf, txt, html, xlsx, xls, csv, ods, pptx, ppt, odp

---

## 4. 변환 카테고리 (C1~C9, 전부 구현)
| # | 변환 | 엔진 | 매핑 | 비고 |
|---|------|------|------|------|
| C1 | 영상 → 영상 | FFmpeg | 1→1 | 해상도·fps·CRF/비트레이트 |
| C2 | 영상 → 음원 | FFmpeg | 1→1 | 오디오 추출·인코딩 (핵심: mp4→mp3) |
| C3 | 음원 → 음원 | FFmpeg | 1→1 | 재인코딩 |
| C4 | 이미지 → 이미지 | Pillow | 1→1 | 품질·해상도 |
| C5 | 영상 → 이미지 | FFmpeg | 1→1 | gif/webp 애니메이션(구간) 또는 단일 프레임(png/jpg) |
| C6 | 이미지 → 영상 | FFmpeg | **N→1** | 여러 이미지 → 슬라이드쇼(concat 데멀서, scale+pad) |
| C7 | 문서 → 문서 | LibreOffice | 1→1 | 계열 제한(워드/시트/프레젠테이션 + pdf) |
| C8 | 이미지 → pdf | Pillow | **N→1** | 여러 이미지 → 다중 페이지 pdf |
| C9 | pdf → 이미지 | pypdfium2 | **1→N** | 각 페이지 → png/jpg (`<stem>_pN.ext`) |

---

## 5. 카테고리·포맷 노출 로직 (`core/registry.py`)
1. 입력 확장자로 **종류**(영상/음원/이미지/문서) 판별.
2. `output_categories_for(입력)` → 가능한 **출력 종류** 목록(같은 종류 먼저). 출력이 하나도 없는 종류는 제외.
3. `output_formats_for(입력, 종류)` → 그 종류의 **출력 포맷** 목록.
4. UI는 `출력: [종류 ▾] [포맷 ▾]` 2단계로 노출(종류 1개면 종류 선택 숨김).

### 노출 제한 메커니즘
- **`IMPLEMENTED_ROUTES`**: 구현된 (입력종류, 출력종류) 집합.
- **`ROUTE_OUTPUTS`**: 경로별 허용 출력·순서. 예) 영상→이미지는 `gif` 우선, 이미지→문서는 `pdf`만,
  pdf→이미지는 png/jpg/webp/tiff/bmp.
- **`ROUTE_INPUT_EXTS`**: 특정 입력에서만 성립. 예) 문서→이미지는 **pdf 입력만**(pypdfium2는 pdf만 연다).
- **문서 계열(`_DOC_FAMILY`/`_FAMILY_OUTPUTS`)**: 워드/스프레드시트/프레젠테이션끼리 + 공통(pdf)만.
  docx→xlsx 같은 무의미 조합 제거. pdf→문서는 미제공(pdf→이미지만).

---

## 6. 옵션 (출력 종류별, 고급 옵션 펼침)
- **음원 출력**: 비트레이트·샘플레이트·채널·볼륨/정규화·구간 자르기 (§9)
- **영상 출력(C1)**: 해상도·프레임레이트·화질(CRF)·오디오 비트레이트·구간 자르기
- **영상→이미지(C5)**: fps(gif/webp)·해상도·구간(애니메이션) / 시작 시점(단일 프레임)
- **이미지 출력(C4)**: 품질(jpg/webp)·해상도
- **이미지→영상(C6)**: 이미지당 표시 시간·영상 크기·fps
- 오디오 출력은 **예상 크기**(비트레이트×길이, 무손실은 PCM)를 표시. 모든 변환에 저장 폴더 선택 가능.

---

## 7. registry 데이터 구조 (실제)
```python
class MediaKind(str, Enum):
    VIDEO = "video"; AUDIO = "audio"; IMAGE = "image"; DOCUMENT = "document"

FORMATS: dict[str, Format]              # 확장자 → Format(ext, kind, can_input, can_output)
IMPLEMENTED_ROUTES: set[(MediaKind, MediaKind)]   # C1~C9
ROUTE_OUTPUTS: dict[route, list[ext]]   # 경로별 허용 출력·순서
ROUTE_INPUT_EXTS: dict[route, set[ext]] # 경로별 허용 입력 확장자

output_categories_for(ext) -> list[MediaKind]
output_formats_for(ext, category=None) -> list[str]
```
UI는 registry에 "이 입력으로 가능한 종류/포맷"만 물어보면 되고, 새 포맷/경로는 데이터만 늘리면 된다.
실제 변환 명령/엔진 선택은 `core/media.py`(`build_command`)와 `gui/worker.py`가 담당한다.

---

## 8. FFmpeg 기능 매핑 (음원·영상)
| 기능 | FFmpeg | 대상 |
|------|--------|------|
| 출력 코덱 | `-c:a`/`-c:v` | 전체 |
| 비트레이트(CBR) | `-b:a`/`-b:v` | C1~C3 |
| 품질(VBR/CRF) | `-q:a` / `-crf` | C1~C3 |
| 샘플레이트 | `-ar` | C2·C3 |
| 채널 | `-ac 1`/`-ac 2` | C2·C3 |
| 볼륨/정규화 | `-af volume=` / `loudnorm` | C2·C3 |
| 구간 자르기 | `-ss`(시작) `-to`(끝), 입력측 배치 | 전체 미디어 |
| 해상도/fps | `-vf scale=` / `-r` | C1 |
| gif 고품질 | `fps,scale,split,palettegen,paletteuse` 단일 패스 | C5 |
| 이미지 시퀀스 | `-f concat` + `scale:pad,format=yuv420p` | C6 |

---

## 9. 음원 출력 고급 옵션 (예: mp4 → mp3)
| 옵션 | 기본값 | FFmpeg |
|------|--------|--------|
| 코덱 | 출력 확장자별(mp3=libmp3lame) | `-c:a` |
| 비트레이트 | 192 kbps (무손실은 미적용) | `-b:a 192k` |
| 샘플레이트 | 원본 | `-ar 44100` |
| 채널 | 원본 | `-ac 1`/`-ac 2` |
| 볼륨/정규화 | 0 dB / off | `-af volume=` · `loudnorm` |
| 구간 자르기 | 전체 | `-ss` / `-to` |

```
# 기본
ffmpeg -i input.mp4 -vn -c:a libmp3lame -b:a 192k output.mp3
# 고급(48kHz·스테레오·30~90초·정규화)
ffmpeg -ss 30 -to 90 -i input.mp4 -vn -c:a libmp3lame -b:a 192k -ar 48000 -ac 2 -af loudnorm output.mp3
```
