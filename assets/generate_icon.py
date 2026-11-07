import math
from PIL import Image, ImageDraw

def create_app_icon(output_path, size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rect with gradient look
    pad = 16
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=48,
        fill=(26, 32, 44, 255),
        outline=(59, 130, 246, 200),
        width=4
    )

    # Inner circular badge
    center = size // 2
    draw.ellipse(
        [center - 70, center - 70, center + 70, center + 70],
        fill=(37, 99, 235, 40),
        outline=(96, 165, 250, 180),
        width=3
    )

    # Stylized package box / trash bin
    # Lid
    draw.rounded_rectangle([center - 45, center - 40, center + 45, center - 30], radius=4, fill=(239, 68, 68, 255))
    draw.rounded_rectangle([center - 15, center - 48, center + 15, center - 40], radius=3, fill=(239, 68, 68, 255))

    # Bin body
    draw.polygon([
        (center - 38, center - 24),
        (center + 38, center - 24),
        (center + 30, center + 45),
        (center - 30, center + 45)
    ], fill=(220, 38, 38, 255))

    # Slits on bin
    for offset in (-14, 0, 14):
        draw.line([(center + offset, center - 12), (center + int(offset * 0.8), center + 33)], fill=(255, 255, 255, 180), width=4)

    # Sparks / cleanup stars
    star_points = [
        (center + 50, center - 35),
        (center - 45, center + 35),
        (center + 42, center + 25)
    ]
    for sx, sy in star_points:
        draw.line([(sx - 6, sy), (sx + 6, sy)], fill=(56, 189, 248, 255), width=2)
        draw.line([(sx, sy - 6), (sx, sy + 6)], fill=(56, 189, 248, 255), width=2)

    img.save(output_path, "PNG")
    print(f"Icon saved to {output_path}")

if __name__ == "__main__":
    import os
    from pathlib import Path
    out = Path.home() / ".local/share/icons/universal-uninstaller.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    create_app_icon(str(out))
