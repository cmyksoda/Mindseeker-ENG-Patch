#!/usr/bin/env python3
"""Japanese character table for Mindseeker's dialogue encoding (PRG text) and tile codes."""

KATAKANA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモラリルレロヤユヨワヲンャュ"
HIRAGANA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもらりるれろやゆよわをん"

DAKUTEN = dict(zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
HANDAKUTEN = dict(zip("はひふへほ", "ぱぴぷぺぽ"))
DAKUTEN_KATA = dict(zip("カキクケコサシスセソタチツテトハヒフヘホウ", "ガギグゲゴザジズゼゾダヂヅデドバビブベボヴ"))
HANDAKUTEN_KATA = dict(zip("ハヒフヘホ", "パピプペポ"))


def build_tile_table():
    """Tile code -> character for the shared font banks (plain, unvoiced glyphs)."""
    table = {0x24: "　"}
    for index, char in enumerate(KATAKANA):
        table[0x40 + index] = char
    for index, char in enumerate("0123456789"):
        table[0x70 + index] = char
    table.update({0x7A: "：", 0x7B: "Ｑ", 0x7C: "ョ", 0x7D: "ッ", 0x7E: "Ａ", 0x7F: "Ｂ"})
    for index, char in enumerate(HIRAGANA):
        table[0x80 + index] = char
    table.update({
        0xAE: "ぁ", 0xAF: "ぃ", 0xB0: "ぉ", 0xB1: "っ", 0xB2: "ゃ", 0xB3: "ゅ", 0xB4: "ょ",
        0xB5: "？", 0xB6: "。", 0xB7: "ー", 0xB8: "゜", 0xB9: "゛", 0xBA: "！",
        0xBB: "°", 0xBC: "″", 0xBD: "＊", 0xBE: "…", 0xBF: "「",
    })
    return table


def build_script_table():
    """Dialogue byte -> character, following the engine at $EDB5 (voiced forms are separate codes)."""
    tiles = build_tile_table()
    table = dict(tiles)
    for code in range(0x02, 0x40):
        if code in (0x10, 0x24):
            continue
        if code < 0x1F:
            base = tiles.get(code | 0x80)
            if base in DAKUTEN:
                table[code] = DAKUTEN[base]
        else:
            base = tiles.get((code - 7) | 0x80)
            if base in HANDAKUTEN:
                table[code] = HANDAKUTEN[base]
    for code in range(0xC0, 0x100):
        plain = code & 0x7F
        if plain < 0x5F:
            base = tiles.get(plain)
            if base in DAKUTEN_KATA:
                table[code] = DAKUTEN_KATA[base]
        else:
            base = tiles.get(plain - 7)
            if base in HANDAKUTEN_KATA:
                table[code] = HANDAKUTEN_KATA[base]
    return table


def decode(data, table=None):
    table = table or build_script_table()
    out = []
    for byte in data:
        if byte == 0x00:
            out.append("\n")
        elif byte == 0xFF:
            out.append("<END>")
        elif byte == 0x10:
            out.append("<N>")
        elif byte == 0xF0:
            out.append("<V>")
        elif byte in table:
            out.append(table[byte])
        else:
            out.append(f"<{byte:02X}>")
    return "".join(out)
