# FormatConverter (macOS) — 실행 안내

macOS 배포본(`FormatConverter.app`)을 쓰기 위한 안내입니다. **두 가지**만 준비하면 됩니다.

> 현재 macOS 빌드는 **Apple Silicon(arm64) 전용**이며 **서명·공증되어 있지 않습니다**.
> 그래서 처음 실행 시 아래 Gatekeeper 우회가 한 번 필요합니다.

## 1. ffmpeg 설치 (필수)
변환 엔진 ffmpeg는 앱에 포함되어 있지 않습니다. [Homebrew](https://brew.sh)로 설치하세요.
```bash
brew install ffmpeg
```
앱은 `/opt/homebrew/bin`(Apple Silicon) 또는 `/usr/local/bin`(Intel)에서 ffmpeg를 자동으로 찾습니다.
Finder에서 실행해도 인식되도록 이 경로들을 직접 탐색합니다.

## 2. 처음 실행 (Gatekeeper 우회)
서명되지 않은 앱이라 그냥 더블클릭하면 "확인되지 않은 개발자" 경고로 막힙니다.
아래 중 **한 가지**로 열면 됩니다(최초 1회).

**방법 A — 우클릭으로 열기 (권장)**
1. `FormatConverter.app`을 **우클릭(또는 Control+클릭) → 열기**
2. 경고 창에서 **[열기]** 클릭 → 이후부터는 더블클릭으로 실행됩니다.

**방법 B — 터미널에서 격리 속성 제거**
```bash
xattr -dr com.apple.quarantine /경로/FormatConverter.app
```

---
문제가 있으면 저장소 이슈로 알려주세요.
