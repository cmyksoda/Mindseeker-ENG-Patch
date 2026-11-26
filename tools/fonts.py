#!/usr/bin/env python3
"""Rasterize the candidate 8x8 fonts to 1-bit glyph grids and draw a comparison sheet."""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "project-data" / "fonts"

# Glyph order of the patch font: tiles $80-$BF of CHR bank $06. The name screen draws an empty
# name with the game's own tiles $BD and $BE, so * and · must stay in those two places.
FONT_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?'-\"…é*·à"

PRESS_START = FONT_DIR / "pressstart2p" / "PressStart2P-Regular.ttf"


def blank():
    return [[0] * 8 for _ in range(8)]


def ellipsis_glyph():
    glyph = blank()
    for x in (0, 3, 6):
        glyph[6][x] = 1
    return glyph


def middle_dot_glyph():
    glyph = blank()
    for y in (3, 4):
        for x in (3, 4):
            glyph[y][x] = 1
    return glyph


# Glyphs drawn here instead of taken from a font: none of the candidates has them at 8x8.
DRAWN_GLYPHS = {"…": ellipsis_glyph, "·": middle_dot_glyph}
# Accented letters for the ASCII-only fonts: (base letter, accent pixels as (x, y) above it).
ACCENTED = {"é": ("e", [(4, 0), (3, 1)]), "à": ("a", [(2, 0), (3, 1)])}


def add_accents(glyphs):
    for char, (base, pixels) in ACCENTED.items():
        glyph = [row[:] for row in glyphs[base]]
        for x, y in pixels:
            glyph[y][x] = 1
        glyphs[char] = glyph


def render_ttf(path, size, y_shift):
    font = ImageFont.truetype(str(path), size)
    glyphs = {}
    for char in FONT_CHARS:
        if char in DRAWN_GLYPHS:
            glyphs[char] = DRAWN_GLYPHS[char]()
            continue
        image = Image.new("L", (16, 16), 0)
        ImageDraw.Draw(image).text((0, 4 + y_shift), char, font=font, fill=255)
        glyphs[char] = [[1 if image.getpixel((x, y + 4)) >= 128 else 0 for x in range(8)]
                        for y in range(8)]
    return glyphs


def load_font8x8():
    """IBM-style 8x8 font from dhepper/font8x8 (public domain); rows are LSB-left."""
    text = (FONT_DIR / "font8x8" / "font8x8_basic.h").read_text()
    rows = re.findall(r"\{\s*((?:0x[0-9A-Fa-f]{2},?\s*){8})\}", text)
    table = [[int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]{2}", row)] for row in rows]
    glyphs = {}
    for char in FONT_CHARS:
        if char in DRAWN_GLYPHS:
            glyphs[char] = DRAWN_GLYPHS[char]()
            continue
        if char in ACCENTED:
            continue
        glyphs[char] = [[(table[ord(char)][y] >> x) & 1 for x in range(8)] for y in range(8)]
    add_accents(glyphs)
    return glyphs


def load_unscii():
    """Unscii-8 by viznut (public domain): `CODE:16 hex digits`, one byte per row, MSB-left."""
    rows = {}
    for line in (FONT_DIR / "unscii" / "unscii-8.hex").read_text().splitlines():
        code, _, bits = line.partition(":")
        if len(bits) == 16:
            rows[int(code, 16)] = [int(bits[i:i + 2], 16) for i in range(0, 16, 2)]
    glyphs = {}
    for char in FONT_CHARS:
        if char in DRAWN_GLYPHS:
            glyphs[char] = DRAWN_GLYPHS[char]()
            continue
        if char in ACCENTED:
            continue
        glyphs[char] = [[(rows[ord(char)][y] >> (7 - x)) & 1 for x in range(8)] for y in range(8)]
    add_accents(glyphs)
    return glyphs


def load_spleen():
    """Spleen 5x8 by Frederic Cambus (BSD): BDF with 5-pixel-wide glyphs, MSB-left."""
    glyphs = {}
    lines = (FONT_DIR / "spleen" / "spleen-5x8.bdf").read_text().splitlines()
    index = 0
    while index < len(lines):
        if lines[index].startswith("ENCODING"):
            code = int(lines[index].split()[1])
            while lines[index] != "BITMAP":
                index += 1
            rows = [int(lines[index + 1 + y], 16) for y in range(8)]
            if 0 <= code < 128 and chr(code) in FONT_CHARS:
                glyphs[chr(code)] = [[(rows[y] >> (7 - x)) & 1 for x in range(8)] for y in range(8)]
        index += 1
    for char, draw in DRAWN_GLYPHS.items():
        glyphs[char] = draw()
    add_accents(glyphs)
    return glyphs


def all_candidates():
    """Top pick first; the build uses whichever name is passed to `candidate()`."""
    return {
        "Press Start 2P": render_ttf(PRESS_START, 8, 0),
        "font8x8 (IBM style)": load_font8x8(),
        "Unscii-8": load_unscii(),
        "Spleen 5x8": load_spleen(),
    }


def candidate(name):
    return all_candidates()[name]


def draw_text(image, glyphs, text, x0, y0, scale, color=(255, 255, 255)):
    pixels = image.load()
    for index, char in enumerate(text):
        glyph = glyphs.get(char)
        if glyph is None:
            continue
        for y in range(8):
            for x in range(8):
                if glyph[y][x]:
                    for dy in range(scale):
                        for dx in range(scale):
                            pixels[x0 + (index * 8 + x) * scale + dx, y0 + y * scale + dy] = color


def comparison_sheet(out_path, fonts, scale=2):
    samples = [
        "ABCDEFGHIJKLMNOPQRSTUVWX",
        "YZ abcdefghijklmnopqrstu",
        "vwxyz .,!?'-\"…é*·à",
        "Hello, AAAA! Let's begin",
        "your psychic training.",
    ]
    label_font = ImageFont.load_default()
    line_height = 12 * scale
    block = len(samples) * line_height + 28
    image = Image.new("RGB", (24 * 8 * scale + 16, block * len(fonts)), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    for row, (name, glyphs) in enumerate(fonts.items()):
        top = row * block
        draw.text((8, top + 4), name, font=label_font, fill=(255, 220, 0))
        for line, sample in enumerate(samples):
            draw_text(image, glyphs, sample, 8, top + 20 + line * line_height, scale)
    image.save(out_path)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "font_candidates.png"
    comparison_sheet(out, all_candidates())
    print(out)
