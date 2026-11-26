#!/usr/bin/env python3
"""Render CHR-ROM as PNG sheets (one per 4K page: 256 tiles, 16x16 grid)."""
import sys
from pathlib import Path
from PIL import Image

HEADER = 16
PALETTE = [(0, 0, 0), (96, 96, 96), (176, 176, 176), (255, 255, 255)]


def decode_tile(tile_bytes):
    rows = []
    for y in range(8):
        low, high = tile_bytes[y], tile_bytes[y + 8]
        rows.append([((low >> (7 - x)) & 1) | (((high >> (7 - x)) & 1) << 1) for x in range(8)])
    return rows


def render_page(chr_data, page, scale=2):
    image = Image.new("RGB", (16 * 8, 16 * 8))
    pixels = image.load()
    for index in range(256):
        offset = page * 4096 + index * 16
        tile = decode_tile(chr_data[offset:offset + 16])
        for y in range(8):
            for x in range(8):
                pixels[(index % 16) * 8 + x, (index // 16) * 8 + y] = PALETTE[tile[y][x]]
    return image.resize((image.width * scale, image.height * scale), Image.NEAREST)


def main():
    rom = Path(sys.argv[1]).read_bytes()
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    prg_size = rom[4] * 16384
    chr_data = rom[HEADER + prg_size:]
    for page in range(len(chr_data) // 4096):
        render_page(chr_data, page).save(out_dir / f"chr_page_{page:02d}.png")


if __name__ == "__main__":
    main()
