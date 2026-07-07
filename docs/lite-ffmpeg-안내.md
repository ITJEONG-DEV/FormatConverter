# FormatConverter (라이트 버전) — ffmpeg 준비 안내

이 라이트 버전(`FormatConverter-lite.exe`)은 파일 크기를 줄이기 위해 **ffmpeg를 포함하지 않습니다.**
ffmpeg는 **영상·음원 변환(mp4 → mp3 등)** 에 필요합니다. 아래 중 **한 가지**만 준비하면 됩니다.

> ffmpeg 없이도 프로그램은 실행되지만, 실제 변환을 시작하면 "ffmpeg를 찾을 수 없습니다"
> 상태 메시지가 표시되고 변환이 진행되지 않습니다.

## 방법 1 — exe 옆에 ffmpeg.exe 두기 (권장, 가장 간단)
1. Windows용 ffmpeg를 받습니다: https://www.gyan.dev/ffmpeg/builds/
   → `ffmpeg-release-essentials.zip` (소스 tar.xz 아님)
2. 압축을 풀고 `bin\ffmpeg.exe`, `bin\ffprobe.exe`를 꺼냅니다.
3. 그 두 파일을 **`FormatConverter-lite.exe`와 같은 폴더**에 복사합니다.

프로그램은 다음 위치에서 ffmpeg를 자동으로 찾습니다:
```
(exe와 같은 폴더)\ffmpeg.exe
(exe와 같은 폴더)\ffmpeg\ffmpeg.exe
(exe와 같은 폴더)\bin\ffmpeg.exe
```

## 방법 2 — 시스템에 ffmpeg 설치
PowerShell에서:
```powershell
winget install Gyan.FFmpeg
```
설치 후 새 창에서 실행하면, 프로그램이 시스템 PATH의 ffmpeg를 자동으로 사용합니다.

---
ffmpeg가 이미 포함되어 바로 쓰고 싶다면 **폴더형(full) 배포본**을 사용하세요.
