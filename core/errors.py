"""변환 실패 메시지를 사용자 친화적인 한글로 변환.

ffmpeg stderr나 Pillow 예외의 기술적 내용을 흔한 원인별로 안내 문구에 매핑한다.
"""
from __future__ import annotations


def friendly_ffmpeg_error(stderr: str, name: str) -> str:
    s = (stderr or "").lower()

    if "does not contain any stream" in s or "output file is empty" in s:
        return f"{name}: 변환할 스트림이 없습니다 (예: 오디오 트랙이 없는 영상)."
    if "permission denied" in s:
        return f"{name}: 저장 위치에 쓸 수 없습니다 (권한을 확인하세요)."
    if "no such file" in s or "could not open file" in s:
        return f"{name}: 입력 파일을 찾을 수 없습니다."
    if "invalid data found" in s or "moov atom not found" in s or "invalid data" in s:
        return f"{name}: 파일이 손상되었거나 지원하지 않는 형식입니다."
    if "unknown encoder" in s or "encoder not found" in s or "cannot load" in s:
        return f"{name}: 이 포맷으로 인코딩할 수 없습니다 (코덱 미지원)."
    if "not divisible by 2" in s or "divisible by 2" in s:
        return f"{name}: 해상도가 코덱 요구(짝수)와 맞지 않습니다."
    if "no space left" in s:
        return f"{name}: 저장 공간이 부족합니다."
    return f"{name}: 변환에 실패했습니다."


def friendly_image_error(exc: Exception, name: str) -> str:
    msg = f"{exc.__class__.__name__}: {exc}".lower()
    if "cannot identify image" in msg or "unidentified" in msg:
        return f"{name}: 지원하지 않거나 손상된 이미지입니다."
    if "permission denied" in msg:
        return f"{name}: 저장 위치에 쓸 수 없습니다 (권한을 확인하세요)."
    if "no such file" in msg or "cannot find" in msg:
        return f"{name}: 입력 파일을 찾을 수 없습니다."
    if "cannot write mode" in msg or "encoder" in msg:
        return f"{name}: 이 형식으로 저장할 수 없습니다."
    return f"{name}: 이미지 변환에 실패했습니다."
