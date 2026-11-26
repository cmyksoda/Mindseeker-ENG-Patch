#!/usr/bin/env python3
"""English versions of the menu, panel and name-entry text that is stored as tile lists.

The game draws these with "PPU lists": records of `hi, lo, count, tiles...` ended by $FF,
loaded through `LDA #lo / STA $00 / LDA #hi / STA $01`. One screen is a nametable in CHR-ROM.
"""

from fonts import FONT_CHARS

BANK_SIZE = 0x2000
BLANK = 0x24
BORDER = 0x01

# Panel menus: (bank, offset in bank, [(ppu address, text), ...]). The panel is seven cells wide;
# a long word may continue on the row below, which the kana menus used for voicing marks.
PANEL_LISTS = [
    (1, 0x09E3, [(0x2117, "YES"), (0x2157, "NO ")]),
    (2, 0x1AA6, [(0x2117, "YES"), (0x2157, "NO ")]),
    (4, 0x1DCC, [(0x211A, "YES"), (0x215A, "NO ")]),
    (4, 0x1DD9, [(0x2117, "YES"), (0x2157, "NO ")]),
    (8, 0x18D6, [(0x2117, "YES"), (0x2157, "NO ")]),
    (9, 0x1225, [(0x2117, "YES"), (0x2157, "NO ")]),
    (8, 0x139B, [(0x2364, "YES NO ")]),
    (1, 0x191D, [(0x22A4, "Inhale")]),
    (1, 0x1927, [(0x22A4, "Hold… ")]),
    (1, 0x1931, [(0x22A4, "Exhale")]),
    (4, 0x1DB7, [(0x2117, "MAP"), (0x2157, "GUIDE")]),
    (4, 0x1E10, [(0x2117, "EXAM"), (0x2157, "TRAIN"), (0x2197, "TRIP")]),
    (4, 0x1E38, [(0x2117, "TRIP")]),
    (4, 0x1E47, [(0x2117, "TRAIN"), (0x2157, "TRIP")]),
    (4, 0x1E68, [(0x2117, "CLAIR."), (0x2157, "PK"), (0x2197, "PRECOG"), (0x21D7, "SET")]),
    (4, 0x1E82, [(0x2117, "FORM"), (0x2157, "BREATH"), (0x2197, "IMAGE")]),
    (4, 0x1E9E, [(0x2117, "USE"), (0x2157, "DON'T")]),
    (14, 0x1EC8, [(0x2117, "USE"), (0x2157, "DON'T")]),
    (5, 0x0620, [(0x2117, "INFO"), (0x2157, "RECORD")]),
    (5, 0x0633, [(0x2117, "INFO"), (0x2157, "RECORD"), (0x2197, "MEDIT.")]),
    (5, 0x064D, [(0x2117, "SAVE")]),
    (5, 0x065A, [(0x2117, "SAVE"), (0x2157, "DATA")]),
    (8, 0x18E3, [(0x2117, "RACE"), (0x2157, "CARD"), (0x2197, "PANEL")]),
]

# The six sayings shown at the ending: (offset in bank 7, lines); centered on rows 13 and 15.
MESSAGE_BANK = 7
MESSAGE_ROWS = (13, 15)
MESSAGES = [
    (0x1D8E, ["The universe is balance,", "with rhythm as its depth."]),
    (0x1DCB, ["Space is what has speed.", "Light itself has none."]),
    (0x1E18, ["Matter reaches for light.", "Light creates matter anew."]),
    (0x1E63, ["Life and the universe", "endure as one whole."]),
    (0x1E94, ["Existence is another", "name for intuition."]),
    (0x1EC8, ["Words are vibrations", "that have settled."]),
]

NAME_GRID_ROWS = (14, 16, 18, 20, 22, 24)
NAME_GRID_LEFT_COLUMNS = (6, 8, 10, 12, 14)
NAME_GRID_RIGHT_COLUMNS = (18, 20, 22, 24, 26)
NAME_GRID_LEFT = ["ABCDE", "FGHIJ", "KLMNO", "PQRST", "UVWXY", "Z.'\" "]
NAME_GRID_RIGHT = ["abcde", "fghij", "klmno", "pqrst", "uvwxy", "z-!? "]
# The kana cursor skipped the 2nd and 4th right-hand cells on rows 3 and 5 (ya/yu/yo). Those
# rows are full now, so each move jumps past its skip test: (PRG bank 0 offset, old, new).
NAME_CURSOR_PATCHES = [
    (0x0442, "c998f0", "4ccfa4"),  # left
    (0x04A5, "c998f0", "4ccfa4"),  # right
    (0x04F0, "c998f0", "4ccfa4"),  # up
    (0x053D, "c998f0", "4ccfa4"),  # down
]

# The title scene is drawn from CHR-ROM nametables.
TITLE_NAMETABLE_BANK = 0x40
MENU_NAMETABLE_BANK = 0x46
# "namco®" as on Namco's US releases, replacing "namcot". One-bit tile rows copied from
# Pac-Man (USA) (Namco): the nine tiles of the logo, then the two holding the top of the ®.
LOGO_TILES = [
    "FFFFE1E1E1E1E1E1", "87C7C0C7CFCECFC7", "F8FC1CFCFC1CFCFC", "FFFFE7E7E7E7E7E7",
    "F0F9393939393938", "FFFFC0C0C0C0FFFF", "1F3F303030303F1F", "E2F272727170F0E0",
    "F494E49408F00000",
]
LOGO_TOP_TILES = ["0000000000000001", "000000000000F008"]
# The title maps CHR bank $02 at tiles $80-$BF. "namcot" was $B0-$B7; the three tiles after it
# were kana for the Japanese attract text.
LOGO_CHR_BANK, LOGO_FIRST_TILE = 0x02, 0xB0
OLD_LOGO_CELLS = (26, 12, 8)
# One row lower than "namcot", so the top of the ® stays inside the rows that use the red palette.
LOGO_ROW, LOGO_COLUMN = 27, 12
# The menu has its own letters in CHR bank $0C, one pixel right of the font's and without an X.
MENU_LETTER_BANK = 0x0C
MENU_LETTERS = dict(zip("CONTIEWGAMUPDS", range(0x09, 0x17)))
MENU_X_TILE = 0x17
MENU_SPEED_CELLS = (19, 12, "TEXT SPEED")

PROMPT_CHR_BANK = 0x47

# The title's attract text: two CHR-ROM nametables scrolled over the starfield. The kana sat on
# every fourth row with voicing marks above; (bank, row, text).
ATTRACT_BANKS = (0x42, 0x43)
ATTRACT_LINES = [
    (0x42, 5, "This software was made"),
    (0x42, 9, "to awaken the psychic"),
    (0x42, 13, "power sleeping deep in"),
    (0x42, 17, "your subconscious."),
    (0x42, 25, "It is closely modeled"),
    (0x42, 29, "on Esper Kiyota's own"),
    (0x43, 3, "experience. Train at"),
    (0x43, 7, "your Mind Level, and"),
    (0x43, 11, "you too will surely"),
    (0x43, 15, "become a psychic…"),
]
ATTRACT_COLUMNS = range(5, 27)
STAR_TILES = {0x75, 0xF7, 0xFA, 0xFE}
TITLE_FONT_BASE = 0xC0
TITLE_STAR_INDEXES = {tile - TITLE_FONT_BASE for tile in STAR_TILES if tile >= TITLE_FONT_BASE}

# CPU window each bank's lists are addressed through.
LIST_WINDOWS = {
    1: 0x8000, 4: 0x8000, 7: 0x8000, 2: 0xA000, 5: 0xA000, 8: 0xA000, 9: 0xA000, 14: 0xC000,
}

# Card test's bottom-row menus (bank 6 at $C000): "＊＊ 1P 2P END" in practice and
# "＊＊ 1P あと N かい" in tests. The ＊＊ slot ignores A, so it is hidden and the cursor starts on 1P.
CARD_PRACTICE_LIST = (3, 0x0C8B)
CARD_TEST_LIST = (3, 0x0C9E)
CARD_MENU_ROW = 27
CARD_COLON = 0x7E
CARD_CURSOR_PATCHES = [  # (PRG offset, original byte, new byte)
    (6 * BANK_SIZE + 0x104B, 0x00, 0x01), (6 * BANK_SIZE + 0x104F, 0x40, 0x60),
    (6 * BANK_SIZE + 0x1090, 0x40, 0x60), (6 * BANK_SIZE + 0x1115, 0x00, 0x01),
    (6 * BANK_SIZE + 0x1119, 0x40, 0x60), (6 * BANK_SIZE + 0x1156, 0x40, 0x60),
]

# Esper Rating screen (list at bank 3 $8DC7, CHR bank 18 in the $40-$7F slot). Labels fill
# columns 6-10; the katakana tiles are redrawn as letters, TOTAL's box in inverted colors.
RATING_LIST = (3, 0x0DC7)
RATING_CHR_BANK = 18
RATING_LABELS = [(5, "TOTAL", True), (8, "CLAIR", False), (10, "PK", False), (12, "PRECG", False)]
RATING_LABEL_COLUMN, RATING_LABEL_WIDTH = 6, 5
RATING_TILES = {True: [0x6F, 0x7F, 0x41, 0x42, 0x46],
                False: [0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x7B, 0x7C]}
RATING_COLORS = {True: (3, 0), False: (1, 3)}  # (background, letter)
RATING_SHIFT = {True: 0, False: 1}  # pixels right, so letters clear the normal boxes' left border
# ド's voicing mark spilled into the TOTAL box's right border tile (rows 0-1, pixel 0).
RATING_SPILL = (0x48, (0, 1))


class ScreenError(Exception):
    pass


class PpuList:
    """A PPU list parsed from PRG, editable by nametable address."""

    def __init__(self, prg, bank, offset):
        self.prg, self.start = prg, bank * BANK_SIZE + offset
        self.cells = {}
        position = self.start
        while prg[position] != 0xFF:
            address = (prg[position] << 8) | prg[position + 1]
            count = prg[position + 2]
            for index in range(count):
                self.cells[address + index] = position + 3 + index
            position += 3 + count
        self.end = position

    def put(self, base, row, column, tiles):
        for index, tile in enumerate(tiles):
            address = base + row * 32 + column + index
            if address not in self.cells:
                raise ScreenError(f"list at PRG {self.start:05X} has no cell at ${address:04X}")
            self.prg[self.cells[address]] = tile

    def replace_everywhere(self, old_tiles, new_tile):
        for position in self.cells.values():
            if self.prg[position] in old_tiles:
                self.prg[position] = new_tile


def find_list_sites(prg, pointer, code_banks):
    sites = []
    for bank in code_banks:
        for index in range(bank * BANK_SIZE, (bank + 1) * BANK_SIZE - 8):
            if (prg[index] == 0xA9 and prg[index + 1] == pointer & 0xFF
                    and prg[index + 2:index + 5] == b"\x85\x00\xA9"
                    and prg[index + 5] == pointer >> 8 and prg[index + 6:index + 8] == b"\x85\x01"):
                sites.append(index)
    return sites


def rewrite_list(prg, bank, offset, records, tiles_for, reserve):
    """Replace a whole list; if the new one is longer, move it and repoint its loaders."""
    start = bank * BANK_SIZE + offset
    old_end = start
    while prg[old_end] != 0xFF:
        old_end += 3 + prg[old_end + 2]

    data = bytearray()
    for address, text in records:
        tiles = tiles_for(text)
        data += bytes([address >> 8, address & 0xFF, len(tiles)]) + bytes(tiles)
    data.append(0xFF)

    moved = None
    if len(data) > old_end - start + 1:
        window = LIST_WINDOWS[bank]
        old_pointer = window + offset
        sites = find_list_sites(prg, old_pointer, range(16))
        if not sites:
            raise ScreenError(f"no loader found for the list at bank {bank} +{offset:04X}")
        new_start = reserve(bank, len(data))
        new_pointer = window + new_start % BANK_SIZE
        for site in sites:
            prg[site + 1] = new_pointer & 0xFF
            prg[site + 5] = new_pointer >> 8
        moved = {"sites": sites, "new_prg_offset": new_start}
        start = new_start

    prg[start:start + len(data)] = data
    return {"bank": bank, "offset": offset, "prg_offset": start, "length": len(data),
            "moved": moved,
            "old_span": (bank * BANK_SIZE + offset, old_end + 1),
            "records": [(address, text) for address, text in records]}


def name_entry(prg, tiles_for):
    """Name-entry screen, message-speed box, rename prompt and the list that redraws under it.

    Edited in place; returns the PRG spans of the four lists and the cursor patches.
    """
    entry = PpuList(prg, 7, 0x0000)
    restore = PpuList(prg, 7, 0x033F)
    for screen in (entry, restore):
        screen.replace_everywhere({0xB8, 0xB9}, BLANK)
    entry.put(0x2000, 4, 13, tiles_for(" Name ") + [BORDER])
    entry.put(0x2000, 6, 10, tiles_for("Player"))
    entry.put(0x2000, 8, 10, tiles_for("Finish    "))
    for screen in (entry, restore):
        screen.put(0x2000, 10, 10, tiles_for("Text Speed   "))
    for row, left, right in zip(NAME_GRID_ROWS, NAME_GRID_LEFT, NAME_GRID_RIGHT):
        for column, char in zip(NAME_GRID_LEFT_COLUMNS, left):
            entry.put(0x2000, row, column, tiles_for(char))
        for column, char in zip(NAME_GRID_RIGHT_COLUMNS, right):
            entry.put(0x2000, row, column, tiles_for(char))
            if 0x2000 + row * 32 + column in restore.cells:
                restore.put(0x2000, row, column, tiles_for(char))
    entry.put(0x2000, 26, 6, tiles_for("Back"))
    entry.put(0x2000, 26, 12, tiles_for("End"))

    speed = PpuList(prg, 7, 0x0206)
    speed.replace_everywhere({0xB8, 0xB9}, BLANK)
    speed.put(0x2800, 4, 11, tiles_for("Text Speed"))

    prompt = PpuList(prg, 7, 0x028C)
    prompt.put(0x2000, 12, 8, tiles_for("Change your name? "))
    prompt.put(0x2000, 16, 21, tiles_for("NO "))
    prompt.put(0x2000, 18, 21, tiles_for("YES"))
    spans = [(screen.start, screen.end + 1) for screen in (entry, restore, speed, prompt)]
    for offset, old, new in NAME_CURSOR_PATCHES:
        if prg[offset:offset + 3] != bytes.fromhex(old):
            raise ScreenError(f"name-entry cursor code is not where it was found (${offset:04X})")
        prg[offset:offset + 3] = bytes.fromhex(new)
        spans.append((offset, offset + 3))
    return spans


def card_menus(prg, tiles_for):
    """Edited in place; returns the PRG spans of both lists and the cursor patches."""
    practice, test = PpuList(prg, *CARD_PRACTICE_LIST), PpuList(prg, *CARD_TEST_LIST)
    for menu in (practice, test):
        menu.put(0x2000, CARD_MENU_ROW, 9, [BLANK, BLANK])
    # The tries-left digit is written at column 21 by the game.
    test.put(0x2000, CARD_MENU_ROW, 16, tiles_for("LEFT") + [CARD_COLON, BLANK, BLANK, BLANK])

    spans = [(menu.start, menu.end + 1) for menu in (practice, test)]
    for offset, old, new in CARD_CURSOR_PATCHES:
        if prg[offset] != old:
            raise ScreenError(f"card menu cursor code is not where it was found ({offset:05X})")
        prg[offset] = new
        spans.append((offset, offset + 1))
    return spans


def rating_labels(prg, chr_data, glyphs):
    """Returns (PRG spans, CHR spans) for the label cells and the redrawn tiles."""
    screen = PpuList(prg, *RATING_LIST)
    chr_spans = []
    letter_tiles = {True: {}, False: {}}

    for row, text, inverted in RATING_LABELS:
        tiles = []
        for char in text:
            pool, assigned = RATING_TILES[inverted], letter_tiles[inverted]
            if char not in assigned:
                if len(assigned) == len(pool):
                    raise ScreenError(f"no tile left for {char!r} on the rating screen")
                assigned[char] = pool[len(assigned)]

                background, letter = RATING_COLORS[inverted]
                shift = RATING_SHIFT[inverted]
                colors = [
                    [letter if x >= shift and line[x - shift] else background for x in range(8)]
                    for line in glyphs[char]
                ]
                planes = [
                    sum((color >> plane & 1) << (7 - x) for x, color in enumerate(line))
                    for plane in (0, 1)
                    for line in colors
                ]
                offset = RATING_CHR_BANK * 0x400 + (assigned[char] - 0x40) * 16
                chr_data[offset:offset + 16] = bytes(planes)
                chr_spans.append((offset, offset + 16))
            tiles.append(assigned[char])
        tiles += [BLANK] * (RATING_LABEL_WIDTH - len(tiles))
        screen.put(0x2000, row, RATING_LABEL_COLUMN, tiles)

    tile, rows = RATING_SPILL
    offset = RATING_CHR_BANK * 0x400 + (tile - 0x40) * 16
    for row in rows:
        chr_data[offset + row] |= 0x80
        chr_data[offset + 8 + row] |= 0x80
    chr_spans.append((offset, offset + 16))
    return [(screen.start, screen.end + 1)], chr_spans


def messages(prg, tiles_for, reserve):
    report = []
    for offset, lines in MESSAGES:
        records = [
            (0x2000 + row * 32 + (32 - len(line)) // 2, line)
            for row, line in zip(MESSAGE_ROWS, lines)
        ]
        report.append(rewrite_list(prg, MESSAGE_BANK, offset, records, tiles_for, reserve))
    return report


def new_game_prompt(chr_data, tiles_for):
    """CHR-ROM nametable shown when NEW GAME would erase a save."""
    base = PROMPT_CHR_BANK * 0x400

    def put(row, column, text, width):
        tiles = tiles_for(text.ljust(width))
        chr_data[base + row * 32 + column:base + row * 32 + column + len(tiles)] = bytes(tiles)

    for row in (6, 8):
        put(row, 7, "", 17)
    put(7, 7, " Erase old data", 17)
    put(9, 7, " and start over?", 17)
    put(17, 12, "NO", 3)
    put(19, 12, "YES", 3)


def title(chr_data, x_glyph):
    """Title logo and the menu's third item; returns the CHR spans written."""
    spans = []

    def write(offset, data):
        chr_data[offset:offset + len(data)] = data
        spans.append((offset, offset + len(data)))

    for index, rows in enumerate(LOGO_TILES + LOGO_TOP_TILES):
        tile = LOGO_FIRST_TILE - 0x80 + index
        write(LOGO_CHR_BANK * 0x400 + tile * 16, bytes.fromhex(rows) + bytes(8))
    table = TITLE_NAMETABLE_BANK * 0x400
    row, column, width = OLD_LOGO_CELLS
    write(table + row * 32 + column, bytes([BLANK] * width))
    logo_end = LOGO_FIRST_TILE + len(LOGO_TILES)
    write(table + LOGO_ROW * 32 + LOGO_COLUMN, bytes(range(LOGO_FIRST_TILE, logo_end)))
    top_column = LOGO_COLUMN + len(LOGO_TILES) - len(LOGO_TOP_TILES)
    write(table + (LOGO_ROW - 1) * 32 + top_column, bytes([logo_end, logo_end + 1]))

    rows = [sum(bit << (6 - x) for x, bit in enumerate(row[:7])) for row in x_glyph]
    write(MENU_LETTER_BANK * 0x400 + MENU_X_TILE * 16, bytes(rows + rows))
    row, column, text = MENU_SPEED_CELLS
    tiles = [BLANK if char == " " else MENU_X_TILE if char == "X" else MENU_LETTERS[char]
             for char in text]
    write(MENU_NAMETABLE_BANK * 0x400 + row * 32 + column, bytes(tiles))
    return spans


def attract(chr_data):
    """Blank everything but the stars, then set the English lines in the title font."""
    for bank in ATTRACT_BANKS:
        for cell in range(bank * 0x400, bank * 0x400 + 960):
            if chr_data[cell] not in STAR_TILES:
                chr_data[cell] = BLANK
    for bank, row, text in ATTRACT_LINES:
        start = (32 - len(text)) // 2
        if start not in ATTRACT_COLUMNS or start + len(text) - 1 not in ATTRACT_COLUMNS:
            raise ScreenError(f"attract line {text!r} leaves the text columns")
        for index, char in enumerate(text):
            if char == " ":
                continue
            glyph = FONT_CHARS.index(char)
            if glyph in TITLE_STAR_INDEXES:
                raise ScreenError(f"attract text uses {char!r}, whose tile is a star")
            chr_data[bank * 0x400 + row * 32 + start + index] = TITLE_FONT_BASE + glyph


def apply(prg, chr_data, tiles_for, reserve, glyphs):
    rating_prg, rating_chr = rating_labels(prg, chr_data, glyphs)
    report = {
        "chr_spans": title(chr_data, glyphs["X"]) + rating_chr,
        "in_place_spans": name_entry(prg, tiles_for) + card_menus(prg, tiles_for) + rating_prg,
        "panels": [rewrite_list(prg, bank, offset, records, tiles_for, reserve)
                   for bank, offset, records in PANEL_LISTS],
        "messages": messages(prg, tiles_for, reserve),
    }
    new_game_prompt(chr_data, tiles_for)
    return report
