## 🎬 FormatConverter {{TAG}}

로컬에서 **영상·음원 파일 포맷을 변환**하는 Windows 데스크톱 프로그램입니다.
파일을 클라우드에 올리지 않고 내 PC에서 바로 변환합니다. (예: mp4 → mp3)

### 🔔 이번 버전 변경사항
<!--CHANGES-->
{{CHANGES}}
<!--/CHANGES-->

### ✨ 주요 기능
- **드래그앤드롭**으로 파일 추가 → 출력 포맷 선택 → 변환
- **영상 → 음원** 변환 (mp4/mkv/mov… → mp3/aac/wav/flac…)
- **고급 옵션**: 비트레이트 · 샘플레이트 · 채널 · 볼륨/정규화 · 구간 자르기
- 변환 **진행률 표시**, UI 멈춤 없음(백그라운드 처리)
- 여러 파일 **일괄 변환**

### 📦 어떤 걸 받아야 하나요? (full vs lite)
| | **full (권장)** | **lite** |
|---|---|---|
| 파일 | `FormatConverter-full-{{VERSION}}.zip` | `FormatConverter-lite-{{VERSION}}.zip` |
| ffmpeg | ✅ 포함 (바로 실행) | ❌ 미포함 (별도 준비) |
| 사용법 | 압축 풀고 `FormatConverter.exe` 실행 | exe 옆에 `ffmpeg.exe`를 두거나 시스템에 설치 |
| 추천 대상 | 대부분의 사용자 | ffmpeg가 이미 있거나 용량을 아끼려는 사용자 |

> ffmpeg는 **영상·음원 변환**에 필요합니다. lite 사용 시 동봉된 `lite-ffmpeg-안내.md`를 참고하세요.

> 🍎 **macOS 사용자**: `FormatConverter-macos-arm64-{{VERSION}}.zip` (Apple Silicon 전용).
> ffmpeg는 `brew install ffmpeg`로 설치하고, 최초 실행 시 우클릭→열기 하세요(동봉된 `macos-안내.md` 참고).
