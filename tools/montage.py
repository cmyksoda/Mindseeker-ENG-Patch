#!/usr/bin/env python3
"""Tile screenshots into one labeled contact sheet: montage.py OUT.png COLS IN1.png IN2.png ..."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    out, cols = sys.argv[1], int(sys.argv[2])
    files = sys.argv[3:]
    images = [Image.open(f).convert("RGB") for f in files]
    width, height = images[0].size
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (width + 4), rows * (height + 14)), (50, 0, 50))
    draw = ImageDraw.Draw(sheet)
    for index, (image, name) in enumerate(zip(images, files)):
        x, y = (index % cols) * (width + 4), (index // cols) * (height + 14)
        sheet.paste(image, (x, y + 12))
        draw.text((x + 2, y), Path(name).stem, fill=(255, 255, 0))
    sheet.save(out)


if __name__ == "__main__":
    main()
