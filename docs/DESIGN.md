# FormatConverter 설계 문서

## 1. 개요
- **목적**: 온라인 변환 서비스(CloudConvert, Convertio) 대체용 로컬 파일 포맷 컨버터
- **기술 스택**: Python 3.11+ / PySide6 + QML(Qt Quick) / FFmpeg / Pillow
- **UI**: 드래그앤드롭, 변환 진행률 표시, UI 멈춤 없음(QThread 백그라운드 처리)
- **배포**: PyInstaller 단일 `.exe` (ffmpeg.exe 번들)

---

## 2. 변환 엔진 매핑
| 카테고리 | 엔진 |
|----------|------|
| 영상/음원 관련 전부 | FFmpeg (`subprocess`) |
| 이미지 → 이미지 | Pillow |
| 문서 (2차 릴리즈) | LibreOffice headless / pandoc |

---

## 3. 지원 포맷 정의

### 영상 (Video)
`mp4`, `avi`, `mkv`, `mov`, `webm`, `flv`, `wmv`, `m4v`, `mpeg`, `ts`, `3gp`

### 음원 (Audio)
`mp3`, `wav`, `aac`, `flac`, `ogg`, `m4a`, `wma`, `opus`, `aiff`

### 이미지 (Image)
`png`, `jpg`, `jpeg`, `webp`, `bmp`, `gif`, `tiff`, `ico`, `heic`

---

## 4. 변환 카테고리 그룹

입력 파일의 종류에 따라 아래 카테고리로 분기하며, 각 카테고리마다 선택 가능한 출력 포맷이 결정된다.

### C1. 영상 → 영상 (Video → Video)
- 코덱/컨테이너 재인코딩
- 입력: 영상 전체 / 출력: 영상 전체
- 예: `mp4 → mkv`, `avi → mp4`, `mov → webm`

### C2. 영상 → 음원 (Video → Audio)  ★핵심 (mp4→mp3)
- 영상에서 오디오 트랙만 추출·인코딩
- 입력: 영상 전체 / 출력: 음원 전체
- 예: `mp4 → mp3`, `mkv → aac`, `webm → wav`

### C3. 음원 → 음원 (Audio → Audio)
- 오디오 재인코딩
- 입력: 음원 전체 / 출력: 음원 전체
- 예: `wav → mp3`, `flac → aac`, `m4a → mp3`

### C4. 이미지 → 이미지 (Image → Image)
- Pillow 기반 변환
- 입력: 이미지 전체 / 출력: 이미지 전체 (`ico`는 출력 전용에 가까움)
- 예: `png → jpg`, `webp → png`, `heic → jpg`

### C5. 영상 → 이미지 (Video → Image)  [옵션·2차]
- **C5a. 단일 프레임 추출**: 특정 시점 → `png`/`jpg`
- **C5b. 애니메이션 GIF**: 구간 → `gif`/`webp`(animated)
- 예: `mp4 → gif`, `mov → png(썸네일)`

### C6. 이미지 → 영상 (Image → Video)  [옵션·2차]
- 여러 이미지(시퀀스) → 슬라이드쇼 영상
- 예: `png 시퀀스 → mp4`

> **1차 릴리즈 범위**: C1, C2, C3, C4
> **2차 릴리즈 범위**: C5, C6, 문서 변환

---

## 5. 카테고리 자동 판별 로직
1. 입력 파일 확장자로 종류 판별 → Video / Audio / Image
2. 종류에 따라 선택 가능한 **출력 카테고리 후보** 제시
   - Video 입력 → [C1 영상, C2 음원, (C5 이미지)]
   - Audio 입력 → [C3 음원]
   - Image 입력 → [C4 이미지, (C6 영상)]
3. 사용자가 출력 포맷 선택 → 해당 카테고리 확정 → 엔진 라우팅

---

## 6. 포맷별 기본 인코딩 옵션 (초안)
| 출력 | 코덱 / 옵션 기본값 |
|------|--------------------|
| mp4 (video) | H.264(libx264) + AAC, CRF 23 |
| webm (video) | VP9 + Opus |
| mkv (video) | 원본 코덱 유지(copy) 우선, 불가 시 재인코딩 |
| mp3 | libmp3lame, 192kbps |
| aac / m4a | AAC, 192kbps |
| wav | PCM 16bit |
| flac | 무손실 |
| opus | 128kbps |
| jpg | 품질 90 |
| png | 무손실 |
| webp | 품질 80 |

향후 UI에서 품질/비트레이트/해상도를 사용자 조절 가능하도록 확장.

---

## 7. 포맷 정의 데이터 구조 (구현 방향)
`core/registry.py`에서 포맷과 카테고리를 데이터로 관리한다.

```python
# 종류
class MediaKind(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"

# 포맷 정의: 확장자 → (종류, 입력가능, 출력가능)
FORMATS = {
    "mp4":  Format("mp4",  MediaKind.VIDEO, can_input=True,  can_output=True),
    "mp3":  Format("mp3",  MediaKind.AUDIO, can_input=True,  can_output=True),
    "ico":  Format("ico",  MediaKind.IMAGE, can_input=True,  can_output=True),
    # ...
}

# 변환 카테고리: (입력 종류, 출력 종류) → 엔진
ROUTES = {
    (VIDEO, VIDEO): FFmpegVideoEngine,
    (VIDEO, AUDIO): FFmpegExtractAudioEngine,
    (AUDIO, AUDIO): FFmpegAudioEngine,
    (IMAGE, IMAGE): PillowImageEngine,
}
```

이렇게 하면 UI는 registry에 "이 입력으로 가능한 출력 목록"만 물어보면 되고,
새 포맷/엔진 추가 시 데이터만 늘리면 된다.

---

## 8. 목표: 예시 페이지 기능 전부 대응
최종 목표는 **CloudConvert / Convertio**의 mp4→mp3 및 미디어 변환 기능을 모두 로컬에서 지원하는 것.
아래 기능을 FFmpeg 옵션으로 매핑한다.

| 예시 페이지 기능 | FFmpeg 매핑 | 대상 카테고리 |
|------------------|-------------|----------------|
| 출력 코덱 선택 | `-c:a` / `-c:v` | 전체 |
| 비트레이트 (CBR) | `-b:a`, `-b:v` | C1~C3 |
| 품질 (VBR) | `-q:a` (mp3 `-qscale`), `-crf` | C1~C3 |
| 샘플레이트(주파수) | `-ar` (44100/48000…) | C2, C3 |
| 채널 (모노/스테레오) | `-ac 1` / `-ac 2` | C2, C3 |
| 볼륨 조절 | `-af volume=` | C2, C3 |
| 볼륨 정규화 | `-af loudnorm` | C2, C3 |
| 구간 자르기(Trim) | `-ss`(시작) `-to`/`-t`(끝) | 전체 |
| 페이드 인/아웃 | `-af afade` / `-vf fade` | C1~C3 |
| 해상도 변경 | `-vf scale=` | C1 |
| 프레임레이트(fps) | `-r` | C1 |
| 회전/뒤집기 | `-vf transpose`/`hflip` | C1 |

---

## 9. C2 (mp4→mp3) 고급 옵션 상세 — 1차 릴리즈
UI 기본값은 자동 적용, "고급 옵션 펼치기"로 아래 조절 가능(예시 페이지 대응).

| 옵션 | UI 컨트롤 | 기본값 | FFmpeg |
|------|----------|--------|--------|
| 오디오 코덱 | 드롭다운(mp3/aac/…) | mp3(libmp3lame) | `-c:a libmp3lame` |
| 비트레이트 | 드롭다운(128/192/256/320) | 192 kbps | `-b:a 192k` |
| 품질 모드 | CBR / VBR 토글 | CBR | VBR 시 `-q:a` |
| 샘플레이트 | 드롭다운(원본/44100/48000/22050) | 원본 유지 | `-ar 44100` |
| 채널 | 원본/모노/스테레오 | 원본 유지 | `-ac 1`/`-ac 2` |
| 볼륨 | 슬라이더(-, +dB) | 0 dB | `-af volume=3dB` |
| 정규화 | 체크박스 | off | `-af loudnorm` |
| 구간 자르기 | 시작/끝 시간 입력 | 전체 | `-ss` / `-to` |
| 페이드 | 인/아웃 초 입력 | off | `-af afade` |

### 예시 명령 (mp4 → mp3, 기본값)
```
ffmpeg -i input.mp4 -vn -c:a libmp3lame -b:a 192k output.mp3
```
### 예시 명령 (고급: 48kHz, 스테레오, 30초~1분30초 구간, 정규화)
```
ffmpeg -ss 30 -to 90 -i input.mp4 -vn -c:a libmp3lame -b:a 192k \
       -ar 48000 -ac 2 -af loudnorm output.mp3
```

> 나머지 카테고리(C1/C3/C4)와 옵션은 2차 이후 동일한 registry/옵션 구조로 확장한다.
