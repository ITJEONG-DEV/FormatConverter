"""앱 아이콘 생성기.

앱 테마색 배경의 둥근 사각형 위에 변환(⇄) 심볼을 그려
assets/app.png / app.ico / app.icns 를 만든다.

사용: python assets/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

S = 1024
HERE = Path(__file__).resolve().parent


def _gradient(top, bot):
    col = Image.new("RGB", (1, S))
    for y in range(S):
        t = y / S
        col.putpixel((0, y), tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
    return col.resize((S, S))


def _arrow(d, y, x0, x1, thick, head, color):
    right = x1 > x0
    shaft_end = x1 - head if right else x1 + head
    d.line([(x0, y), (shaft_end, y)], fill=color, width=thick)
    if right:
        d.polygon([(x1, y), (x1 - head, y - head), (x1 - head, y + head)], fill=color)
    else:
        d.polygon([(x1, y), (x1 + head, y - head), (x1 + head, y + head)], fill=color)


def build_png() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255
    )
    img.paste(_gradient((66, 133, 244), (32, 74, 176)), (0, 0), mask)

    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    thick = int(S * 0.055)
    head = int(S * 0.10)
    _arrow(d, int(S * 0.40), int(S * 0.26), int(S * 0.74), thick, head, white)  # →
    _arrow(d, int(S * 0.60), int(S * 0.74), int(S * 0.26), thick, head, white)  # ←
    return img


def main():
    img = build_png()
    img.save(HERE / "app.png")
    img.save(
        HERE / "app.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    try:
        img.save(HERE / "app.icns")
        print("app.png / app.ico / app.icns 생성 완료")
    except Exception as exc:  # noqa: BLE001
        print(f"app.png / app.ico 생성 완료 (icns 실패: {exc})")


if __name__ == "__main__":
    main()
