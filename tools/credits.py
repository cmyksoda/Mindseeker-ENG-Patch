#!/usr/bin/env python3
"""English staff credits for the ending, set in the patch font instead of the kanji name art.

The ending (bank 0 at $A000, $AC0A-$AEDD) shows eight PPU lists, the last one as a roll.
The patch maps a white copy of the font at $1800 and a pink copy at $1C00 for every screen.

usage: credits.py   (renders before/after pictures into project-data/credits/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fonts import FONT_CHARS, ellipsis_glyph
from screens import BLANK, ScreenError, find_list_sites

BANK_SIZE = 0x2000
CODE_BANK = 0
WINDOW = 0xA000
LIST_SPAN = (0x12A5, 0x1518)
LIST_POINTERS = [0xB2A5, 0xB2E8, 0xB35B, 0xB380, 0xB3BC, 0xB3E1, 0xB406, 0xB453]

FONT_SOURCE_BANK = 0x06
WHITE_BANK, PINK_BANK = 0x78, 0x79
PINK_OFFSET = 0x40
# Immediates of the `LDA #bank / STA $B000 (or $B800)` pairs in bank 0.
WHITE_BANK_IMMEDIATES = (0x0C85, 0x0D22, 0x0E2F)
PINK_BANK_IMMEDIATES = (0x0D27, 0x0E34)
ORIGINAL_CHR = {0x0C85: 0x73, 0x0D22: 0x74, 0x0E2F: 0x76, 0x0D27: 0x75, 0x0E34: 0x77}

ROLE_ROW, NAME_ROW = 21, 23

# (row, text, pink); rows are nametable rows, every line is centered.
SCREENS = [
    [(ROLE_ROW, "Supervisor", False), (NAME_ROW, "Masuaki Kiyota", False)],
    [(ROLE_ROW, "Executive Director", False), (NAME_ROW, "VSP & PSI", False)],
    [(ROLE_ROW, "Planning", False), (NAME_ROW, "Koji Suzuki", False)],
    [(ROLE_ROW, "Technical Director", False), (NAME_ROW, "Kiyokazu Ikeda", False),
     (25, "Programming  STARGATE", True)],
    [(ROLE_ROW, "Art", False), (NAME_ROW, "Takahiro Hatanaka", False)],
    [(ROLE_ROW, "Music", False), (NAME_ROW, "Kosei Miura", False)],
    [(20, "Editing", False), (22, "Koji Suzuki", False), (24, "Kiyokazu Ikeda", False),
     (26, "Takahiro Hatanaka", False)],
    # The roll: the original puts a 16x16 line on rows 0-1 and every four rows after.
    [(1, "Special Thanks", False)] + [(5 + 4 * index, name, False) for index, name in enumerate([
        "Toshio Tsurumaru", "Miyuki Shibayama", "Miwa Matsubara", "Issei Ki",
        "Kunihiko Kamiyama", "Taeko Kitajima", "Tomoo Yamane",
    ])],
]


def font_installed(chr_data):
    expected = [sum(bit << (7 - x) for x, bit in enumerate(row)) for row in ellipsis_glyph()]
    offset = FONT_SOURCE_BANK * 0x400 + FONT_CHARS.index("…") * 16
    return list(chr_data[offset:offset + 8]) == expected


def install_font_copies(chr_data):
    """White copy as is; pink copy moves color 3 to color 2 by clearing the low plane."""
    source = chr_data[FONT_SOURCE_BANK * 0x400:(FONT_SOURCE_BANK + 1) * 0x400]
    chr_data[WHITE_BANK * 0x400:(WHITE_BANK + 1) * 0x400] = source
    pink = bytearray(source)
    for tile in range(0, len(pink), 16):
        pink[tile:tile + 8] = bytes(8)
    chr_data[PINK_BANK * 0x400:(PINK_BANK + 1) * 0x400] = pink


def screen_list(lines, tiles_for):
    data = bytearray()
    for row, text, pink in lines:
        tiles = tiles_for(text)
        if any(not 0x80 <= tile < 0xC0 and tile != BLANK for tile in tiles):
            raise ScreenError(f"credits line {text!r} needs a tile outside the font copy")
        if pink:
            tiles = [tile if tile == BLANK else tile + PINK_OFFSET for tile in tiles]
        address = 0x2000 + row * 32 + (32 - len(tiles)) // 2
        data += bytes([address >> 8, address & 0xFF, len(tiles)]) + bytes(tiles)
    return data + b"\xFF"


def apply(prg, chr_data, tiles_for, reserve):
    """Call after the English font is in CHR bank $06: the credits use copies of it."""
    if not font_installed(chr_data):
        raise ScreenError("credits: install the English font in CHR bank $06 first")
    sites = []
    for pointer in LIST_POINTERS:
        found = find_list_sites(prg, pointer, [CODE_BANK])
        if len(found) != 1:
            raise ScreenError(
                f"credits: expected one loader for ${pointer:04X}, found {len(found)}")
        sites += found
    for offset, bank in ORIGINAL_CHR.items():
        if prg[CODE_BANK * BANK_SIZE + offset] != bank:
            raise ScreenError(f"credits: no CHR bank ${bank:02X} immediate at bank 0 +{offset:04X}")

    lists = [screen_list(lines, tiles_for) for lines in SCREENS]
    start, end = (CODE_BANK * BANK_SIZE + offset for offset in LIST_SPAN)
    if sum(map(len, lists)) > end - start:
        raise ScreenError("credits: the English lists outgrow the original span")
    report, position = [], start
    for site, data in zip(sites, lists):
        pointer = WINDOW + position % BANK_SIZE
        prg[site + 1], prg[site + 5] = pointer & 0xFF, pointer >> 8
        prg[position:position + len(data)] = data
        report.append({"prg_offset": position, "length": len(data), "loader": site})
        position += len(data)
    prg[position:end] = bytes([0xFF]) * (end - position)

    for offset in WHITE_BANK_IMMEDIATES:
        prg[CODE_BANK * BANK_SIZE + offset] = WHITE_BANK
    for offset in PINK_BANK_IMMEDIATES:
        prg[CODE_BANK * BANK_SIZE + offset] = PINK_BANK
    install_font_copies(chr_data)
    return {"lists": report, "span": (start, end), "used": position - start,
            "chr_banks": [WHITE_BANK, PINK_BANK]}


# --- preview ---------------------------------------------------------------------------------

PREVIEW_COLORS = [(0, 0, 0), (0, 0, 0), (255, 119, 230), (255, 255, 255)]  # $0F, unused, $24, $30


def loaded_lists(prg):
    """Lists and CHR banks the ending's code actually uses, read back from the code."""
    bank = prg[CODE_BANK * BANK_SIZE:(CODE_BANK + 1) * BANK_SIZE]
    pointers = []
    for index in range(len(bank) - 8):
        if (bank[index] == 0xA9 and bank[index + 2:index + 5] == b"\x85\x00\xA9"
                and bank[index + 6:index + 8] == b"\x85\x01" and 0x0C00 <= index < 0x0E50):
            pointers.append((bank[index + 5] << 8 | bank[index + 1]) - WINDOW)
    low = [bank[offset] for offset in WHITE_BANK_IMMEDIATES]
    high = [bank[offset] for offset in PINK_BANK_IMMEDIATES]
    chr_banks = [(low[0], high[0])] * 2 + [(low[1], high[0])] * 5 + [(low[2], high[1])]
    return [(bank, pointer, chr_pair) for pointer, chr_pair in zip(pointers, chr_banks)]


def render(bank, offset, chr_data, chr_pair, scale=3):
    from PIL import Image

    image = Image.new("RGB", (256, 240))
    pixels = image.load()
    while bank[offset] != 0xFF:
        address, count = bank[offset] << 8 | bank[offset + 1], bank[offset + 2]
        for index, tile in enumerate(bank[offset + 3:offset + 3 + count]):
            cell = (address & 0x3FF) + index
            if tile < 0x80 or cell >= 960:
                continue
            base = chr_pair[tile >= 0xC0] * 0x400 + (tile & 0x3F) * 16
            for y in range(8):
                low, high = chr_data[base + y], chr_data[base + y + 8]
                for x in range(8):
                    color = (low >> (7 - x) & 1) | (high >> (7 - x) & 1) << 1
                    pixels[(cell % 32) * 8 + x, (cell // 32) * 8 + y] = PREVIEW_COLORS[color]
        offset += 3 + count
    return image.resize((256 * scale, 240 * scale), Image.NEAREST)


def main():
    import build
    import fonts

    root = Path(__file__).resolve().parent.parent
    out = root / "project-data" / "credits"
    out.mkdir(parents=True, exist_ok=True)
    rom = build.ROM_PATH.read_bytes()
    prg = bytearray(rom[build.HEADER:build.HEADER + build.PRG_SIZE])
    chr_data = bytearray(rom[build.HEADER + build.PRG_SIZE:])
    for number, (bank, offset, pair) in enumerate(loaded_lists(prg), 1):
        render(bank, offset, chr_data, pair).save(out / f"jp_screen_{number}.png")

    build.install_font(chr_data, fonts.candidate("Press Start 2P"))
    report = apply(prg, chr_data,
                   lambda text: [build.code_tile(build.char_code(c)) for c in text], None)
    for number, (bank, offset, pair) in enumerate(loaded_lists(prg), 1):
        render(bank, offset, chr_data, pair).save(out / f"en_screen_{number}.png")
    print(f"credits lists: {report['used']} of {report['span'][1] - report['span'][0]} bytes")


if __name__ == "__main__":
    main()
