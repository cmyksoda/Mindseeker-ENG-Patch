#!/usr/bin/env python3
"""Build the English Mindseeker ROM and IPS patch from the untouched Japanese ROM.

usage: build.py [--font NAME]
Reads script/dialogue_jp.json (from dump_script.py) and script/translation/*_en.json,
writes dist/Mindseeker (English).nes, dist/mindseeker_en.ips, dist/mindseeker_en.tbl and
build/build_report.json (everything verify.py needs).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import credits
import fonts
import screens
from asm6502 import assemble
from ips import make_ips

ROOT = Path(__file__).resolve().parent.parent
ROM_PATH = ROOT / "Mindseeker (Japan).nes"
HEADER = 16
BANK_SIZE = 0x2000
PRG_SIZE = 0x20000
FIXED_BANK = 15

LINE_WIDTH = 24
PAGE_LINES = 3
ONELINE_WIDTH = 10

# Psi Land's hostess box. Only some of these load their pointer right before `JSR $EC16`.
ONELINE_IDS = {
    "D08_B3B1", "D08_B3B9", "D08_B3C2", "D08_B3CB", "D08_B3D4", "D08_B3DD", "D08_B3E4", "D08_B3EB",
    "D08_B3F1", "D08_B3F9", "D08_B402", "D08_B40A",
}
# Sites that reach the line-2 printer $E89F through shared code instead of a direct JSR.
LINE2_SITES = {2 * BANK_SIZE + 0x07E4, 2 * BANK_SIZE + 0x0A4F}
# `$EC16` clears the hostess box: `LDA #$03 / STA $01` (start column) and `LDA #$08 / STA $03`
# (width). One column left and two wider gives 10 cells with a gap before her face.
BOX_CLEAR_PATCHES = [(0xEC1E, 0x03, 0x02), (0xEC26, 0x08, 0x0A)]
# The title scene's kana bank. It takes the font too, minus the tiles its starfield uses.
TITLE_FONT_BANK = 0x03
# $06 is the usual font bank; the computer room swaps in $0E, a kana/katakana hybrid.
FONT_CHR_BANKS = (0x06, 0x0E)

NEWLINE, NAME, VALUE, PAGE, END = 0x00, 0x01, 0x02, 0x03, 0xFF
SPACE = 0xC0
DIGIT_BASE = 0xC1
COLON = 0xCB
PAIR_CODES = list(range(0x04, 0x80)) + list(range(0xD0, 0xFF))

# Run-time value codes the engine understands in the $0500 buffer.
WORD_TOKENS = {3: "Clairvoyance", 4: "Psychokinesis", 5: "Precognition"}
VALUE_SKIP = 0x06
POWER_NAME_WIDTH = max(len(word) for word in WORD_TOKENS.values())

# Strings whose 4-wide {V} runs are a power name rather than a number (run indexes).
POWER_NAME_RUNS = {
    "D02_BB24": [0], "D09_B383": [0], "D10_8164": [0], "D10_8181": [0], "D10_819C": [0],
    "D10_81B2": [0], "D04_9F25": [0], "D04_9F6D": [0, 1],
}

# 4-byte kana power names the game copies into the value buffer: (bank, cpu address, tokens).
POWER_NAME_TABLES = [
    (2, 0xB9A3, [4, 5, 3]),
    (6, 0xDF77, [3, 4, 5]),
    (9, 0xAFC9, [4, 5, 3]),
]

# The fixed bank's panel clear: `LDA #$07 / STA $03` = 7 columns from the cursor column, which
# stops one short of the panel's last cell. Seven-letter labels need all eight cleared.
PANEL_CLEAR_COLUMNS = (FIXED_BANK, 0xF400, bytes([0xA9, 0x07, 0x85, 0x03]), 8)

# Extractor entries that are not dialogue (mouth-sprite tile numbers, a data pointer).
NOT_TEXT = {"D04_B9B8", "D10_8422"}

# Kana codes $EF50 turns into the five mouth shapes (a i u e o), plus hold and closed.
MOUTH_VOWELS = {"a": 0x80, "i": 0x81, "u": 0x82, "e": 0x83, "o": 0x84, "y": 0x81}
MOUTH_HOLD, MOUTH_CLOSED = 0xB7, 0x24
MOUTH_CLOSED_LETTERS = "bmp"

# The old printers this build overwrites, and the only entry points other code may use.
ENGINE_REGIONS = [(0xE89F, 0xEC01), (0xED6A, 0xEEDD)]
ENGINE_ENTRIES = {0xE89F, 0xE8D9, 0xEAEB, 0xED80, 0xED96, 0xEDB0}

CALL_E89F = "209fe8"


class BuildError(Exception):
    pass


def char_code(char):
    if char == " ":
        return SPACE
    if char.isdigit() and char.isascii():
        return DIGIT_BASE + int(char)
    if char == ":":
        return COLON
    index = fonts.FONT_CHARS.find(char)
    if index < 0:
        raise BuildError(f"character {char!r} is not in the font")
    return 0x80 + index


def code_tile(code):
    """Background tile a plain text code ($80-$CF) is drawn with."""
    return code if code < 0xC0 else high_tiles()[code - 0xC0]


def high_tiles():
    return [screens.BLANK] + list(range(0xF0, 0xFA)) + [0xFE] + [screens.BLANK] * 4


# --- layout ---------------------------------------------------------------------------------

def parse_cells(text, name_runs):
    """Turn final English text into words of (code, width) cells plus break markers."""
    items, word = [], []
    run_index = 0
    position = 0

    def flush():
        nonlocal word
        if word:
            items.append(word)
            word = []

    while position < len(text):
        if text.startswith("{NAME}", position):
            word.extend([(NAME, 1)] * 4)
            position += 6
        elif text.startswith("{V}", position):
            count = 0
            while text.startswith("{V}", position):
                count += 1
                position += 3
            if run_index in name_runs:
                if count != 4:
                    raise BuildError("a power-name run must be 4 wide")
                word.append((VALUE, POWER_NAME_WIDTH))
                word.extend([(VALUE, 0)] * 3)
            else:
                word.extend([(VALUE, 1)] * count)
            run_index += 1
        elif text.startswith("{P}", position):
            flush()
            items.append("page")
            position += 3
        elif text[position] == "\n":
            flush()
            items.append("line")
            position += 1
        elif text[position] == " ":
            flush()
            position += 1
        else:
            word.append((char_code(text[position]), 1))
            position += 1
    flush()
    return items


def layout(text, name_runs=(), width=LINE_WIDTH, first_page_lines=PAGE_LINES):
    """Wrap into pages of lines; each line is a list of text codes."""
    pages, lines, line, column = [], [], [], 0

    def end_line():
        nonlocal line, column
        lines.append(line)
        line, column = [], 0
        if len(lines) == (first_page_lines if not pages else PAGE_LINES):
            end_page()

    def end_page():
        nonlocal lines
        if lines:
            pages.append(lines)
            lines = []

    for item in parse_cells(text, name_runs):
        if item == "line":
            end_line()
            continue
        if item == "page":
            if line:
                end_line()
            end_page()
            continue
        word_width = sum(cell[1] for cell in item)
        if word_width > width:
            raise BuildError(f"word wider than a line in {text!r}")
        if column and column + 1 + word_width > width:
            end_line()
        if column:
            line.append(SPACE)
            column += 1
        line.extend(cell[0] for cell in item)
        column += word_width
    if line:
        end_line()
    end_page()
    return pages


def encode_pages(pages, lead_lines=0, end_wait=False):
    out = [NEWLINE] * lead_lines
    for page_index, lines in enumerate(pages):
        if page_index:
            out.append(PAGE)
        for line_index, line in enumerate(lines):
            if line_index:
                out.append(NEWLINE)
            out.extend(line)
    if end_wait:
        out.append(PAGE)
    return out


def original_ends_with_wait(raw, start_line=1):
    """Replay the kana printer: does the string end on a box its own wait-and-clear emptied?

    Newlines after that clear only move the cursor, so the next text still starts on a clean box.
    """
    line, column, cleared = start_line, 0, False
    for byte in raw:
        if byte != 0x00:
            cleared = False
            column += 1
            if column < LINE_WIDTH:
                continue
        column = 0
        if line == PAGE_LINES:
            line, cleared = 1, True
        else:
            line += 1
    return cleared


# --- compression ----------------------------------------------------------------------------

def choose_pairs(strings):
    """Greedy dual-tile encoding over plain letter codes; returns (pairs, compressed strings)."""
    work = [list(codes) for codes in strings]
    pairs = []
    for code in PAIR_CODES:
        counts = Counter()
        for codes in work:
            previous = None
            for index in range(len(codes) - 1):
                a, b = codes[index], codes[index + 1]
                if 0x80 <= a < 0xD0 and 0x80 <= b < 0xD0:
                    # Skip the overlap in runs like "aaa" so counts match what replacement saves.
                    if previous == index - 1 and a == b and codes[index - 1] == a:
                        previous = None
                        continue
                    counts[(a, b)] += 1
                    previous = index

        if not counts:
            break
        (first, second), count = counts.most_common(1)[0]
        if count < 2:
            break

        pairs.append((first, second))
        for codes in work:
            index, out = 0, []
            while index < len(codes):
                if index + 1 < len(codes) and codes[index] == first and codes[index + 1] == second:
                    out.append(code)
                    index += 2
                else:
                    out.append(codes[index])
                    index += 1
            codes[:] = out
    return pairs, work


def expand(data, pairs):
    """Inverse of the pair encoding, for verification and the table file."""
    out = []
    for byte in data:
        if byte in PAIR_CODES and PAIR_CODES.index(byte) < len(pairs):
            out.extend(pairs[PAIR_CODES.index(byte)])
        else:
            out.append(byte)
    return out


# --- ROM helpers ----------------------------------------------------------------------------

def prg_offset(bank, cpu):
    return bank * BANK_SIZE + (cpu & 0x1FFF)


def bank_tail_free(prg, bank):
    """The $FF padding at the end of a bank, keeping one $FF as the previous data's terminator."""
    end = (bank + 1) * BANK_SIZE
    start = end
    while start > bank * BANK_SIZE and prg[start - 1] == 0xFF:
        start -= 1
    start += 1
    return (start, end) if end - start >= 32 else None


def merge_regions(regions):
    merged = []
    for start, end in sorted(regions):
        if merged and start <= merged[-1][1] and start // BANK_SIZE == merged[-1][0] // BANK_SIZE:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(region) for region in merged]


def hook_bank_writes(prg, set_8000):
    """Route every `STA $E000` through set_8000 so the engine knows the scene's $8000 bank."""
    sites = []
    for index in range(len(prg) - 2):
        if prg[index:index + 3] == b"\x8D\x00\xE0":
            if prg[index - 2] != 0x09 and prg[index - 2] != 0xA9:
                raise BuildError(f"unexpected $E000 write at PRG {index:05X}")
            prg[index:index + 3] = bytes([0x20, set_8000 & 0xFF, set_8000 >> 8])
            sites.append(index)
    return sites


def check_engine_entries(prg):
    """No code outside the old printers may jump into them except at the kept entry points."""
    for index in range(len(prg) - 2):
        if prg[index] not in (0x20, 0x4C):
            continue
        target = prg[index + 1] | (prg[index + 2] << 8)
        if (not any(low <= target < high for low, high in ENGINE_REGIONS)
                or target in ENGINE_ENTRIES):
            continue
        source = 0xE000 + index % BANK_SIZE if index // BANK_SIZE == FIXED_BANK else None
        inside = source is not None and any(low <= source < high for low, high in ENGINE_REGIONS)
        # `CMP #$20 / BEQ` and `INC $20 / JMP` read as JSR/JMP when started one byte late.
        false_positive = prg[index - 1] in (0xC9, 0xE6)
        if not inside and not false_positive:
            raise BuildError(f"outside entry into replaced code: PRG {index:05X} -> ${target:04X}")


def widen_panel_clear(prg):
    bank, cpu, expected, columns = PANEL_CLEAR_COLUMNS
    offset = prg_offset(bank, cpu)
    if bytes(prg[offset - 1:offset + 3]) != expected:
        raise BuildError("panel clear routine is not where it was found")
    prg[offset] = columns
    return offset


def widen_box_clear(prg):
    offsets = []
    for cpu, expected, value in BOX_CLEAR_PATCHES:
        offset = prg_offset(FIXED_BANK, cpu)
        if prg[offset] != expected:
            raise BuildError(f"hostess box clear is not where it was found (${cpu:04X})")
        prg[offset] = value
        offsets.append(offset)
    return offsets


def install_title_font(chr_data, glyphs):
    """The title scene's kana bank becomes the font too, except the tiles its stars use."""
    for index, char in enumerate(fonts.FONT_CHARS):
        if index in screens.TITLE_STAR_INDEXES:
            continue
        offset = TITLE_FONT_BANK * 0x400 + index * 16
        chr_data[offset:offset + 16] = tile_bytes(glyphs[char])


def tile_bytes(glyph):
    """8x8 one-bit glyph as a 2bpp tile in color 3, like the game's own font."""
    rows = [sum(bit << (7 - x) for x, bit in enumerate(row)) for row in glyph]
    return bytes(rows + rows)


def install_font(chr_data, glyphs):
    for bank in FONT_CHR_BANKS:
        for index, char in enumerate(fonts.FONT_CHARS):
            offset = bank * 0x400 + index * 16
            chr_data[offset:offset + 16] = tile_bytes(glyphs[char])


def mouth_shapes():
    """Per font tile: the vowel's shape, lips shut for b/m/p and punctuation, otherwise hold."""
    shapes = []
    for char in fonts.FONT_CHARS:
        lower = fonts.ACCENTED[char][0] if char in fonts.ACCENTED else char.lower()
        if lower in MOUTH_VOWELS:
            shapes.append(MOUTH_VOWELS[lower])
        elif lower in MOUTH_CLOSED_LETTERS or not char.isalpha():
            shapes.append(MOUTH_CLOSED)
        else:
            shapes.append(MOUTH_HOLD)
    return shapes


def engine_source(pairs, bank_slots):
    def db(label, values):
        lines = [f"{label}:"]
        for start in range(0, len(values), 16):
            lines.append("    .db " + ", ".join(f"${v:02X}" for v in values[start:start + 16]))
        return "\n".join(lines)

    words, starts = [], []
    for token in sorted(WORD_TOKENS):
        starts.append(len(words))
        words.extend(char_code(c) for c in WORD_TOKENS[token])
        words.append(0)
    padded = pairs + [(SPACE, SPACE)] * (len(PAIR_CODES) - len(pairs))
    tables = [
        ".org $EAEE",
        db("pair_first", [p[0] for p in padded]),
        db("text_banks", [0x70 | bank for bank in bank_slots] + [0x70] * (8 - len(bank_slots))),
        db("word_starts", starts),
        db("words", words),
        ".org $EDB3",
        db("pair_second", [p[1] for p in padded]),
        db("mouth_shapes", mouth_shapes()),
    ]
    return (ROOT / "tools" / "engine.asm").read_text() + "\n" + "\n".join(tables) + "\n"


def install_engine(prg, pairs, bank_slots):
    """Assemble the engine, hook the game's own bank writes, then write the engine in."""
    chunks, symbols = assemble(engine_source(pairs, bank_slots))
    hooks = hook_bank_writes(prg, symbols["set_8000"])
    spans = sorted((address, address + len(data)) for address, data in chunks.items())
    for (start, end), (next_start, _) in zip(spans, spans[1:]):
        if end > next_start:
            raise BuildError(f"engine chunks overlap at ${next_start:04X}")
    for address, data in chunks.items():
        if not any(low <= address and address + len(data) <= high for low, high in ENGINE_REGIONS):
            raise BuildError(f"engine chunk ${address:04X}+{len(data)} leaves the old printer area")
        offset = prg_offset(FIXED_BANK, address)
        prg[offset:offset + len(data)] = data
    return symbols, spans, hooks


# --- script ---------------------------------------------------------------------------------

def load_translations():
    english = {}
    for path in sorted((ROOT / "script" / "translation").glob("*_en.json")):
        for entry in json.loads(path.read_text()):
            english[entry["id"]] = entry
    overrides = json.loads((ROOT / "script" / "overrides.json").read_text())
    for string_id, final in overrides.items():
        english.setdefault(string_id, {"id": string_id, "literal": "", "note": ""})["final"] = final
    return english


def normalize(text):
    return text.replace("...", "…").replace("’", "'").strip("\n")


def site_kind(site):
    if site["id"] in ONELINE_IDS:
        return "oneline"
    if site["next"] == CALL_E89F or site["prg_offset"] in LINE2_SITES:
        return "line2"
    return "dialogue"


def lead_lines_for(site, strings, compiled_lines):
    """Lines already on screen when an $E89F string starts: the prompt printed just before it."""
    lines = [
        compiled_lines[other["id"]]
        for other in strings
        for other_site in other["sites"]
        if other_site["bank"] == site["bank"]
        and 0 < site["prg_offset"] - other_site["prg_offset"] <= 0x40
        and other["id"] in compiled_lines
        and site_kind(other_site) != "line2"
    ]
    if not lines:
        raise BuildError(f"no prompt found before line-2 site {site['prg_offset']:05X}")
    return max(lines)


def compile_script(strings, english):
    """Return variants: one compiled string per (id, lead lines), with the sites that use it."""
    variants = {}
    laid_out = {}
    for string in strings:
        final = normalize(english[string["id"]]["final"])
        name_runs = POWER_NAME_RUNS.get(string["id"], ())
        kinds = {site_kind(site) for site in string["sites"]}
        if len(kinds) > 1 and "oneline" in kinds:
            raise BuildError(f"{string['id']} is used both as a one-liner and as dialogue")
        if "oneline" in kinds:
            pages = layout(final, name_runs, width=ONELINE_WIDTH)
            if len(pages) != 1 or len(pages[0]) != 1:
                raise BuildError(
                    f"{string['id']}: one-liner {final!r} needs more than {ONELINE_WIDTH} cells")
            variants[(string["id"], 0)] = {
                "codes": encode_pages(pages),
                "pages": pages,
                "sites": string["sites"],
            }
            continue
        laid_out[string["id"]] = layout(final, name_runs)

    first_page_lines = {
        string_id: len(pages[0]) if len(pages) == 1 else PAGE_LINES
        for string_id, pages in laid_out.items()
    }

    for string in strings:
        if string["id"] not in laid_out:
            continue
        final = normalize(english[string["id"]]["final"])
        name_runs = POWER_NAME_RUNS.get(string["id"], ())
        raw = bytes.fromhex(string["raw"])
        for site in string["sites"]:
            lead = 0
            site_pages = laid_out[string["id"]]
            if site_kind(site) == "line2":
                lead = lead_lines_for(site, strings, first_page_lines)
                site_pages = layout(final, name_runs, first_page_lines=PAGE_LINES - lead)
                if lead >= PAGE_LINES or len(site_pages) != 1:
                    raise BuildError(f"{string['id']}: does not fit under a {lead}-line prompt")
            end_wait = original_ends_with_wait(raw, 2 if lead else 1)
            variant = variants.setdefault((string["id"], lead), {
                "codes": encode_pages(site_pages, lead, end_wait), "pages": site_pages, "sites": [],
                "lead": lead, "end_wait": end_wait,
            })
            variant["sites"].append(site)
    return variants


class FreeSpace:
    """Free PRG regions, shared by relocated tile lists and the compiled script."""

    def __init__(self, prg, regions):
        self.prg = prg
        self.regions = [[start, end] for start, end in regions]
        for start, end in self.regions:
            prg[start:end] = b"\xFF" * (end - start)

    def by_bank(self):
        totals = Counter()
        for start, end in self.regions:
            totals[start // BANK_SIZE] += end - start
        return totals

    def take(self, size, banks):
        """Best fit: the smallest region in the given banks that holds `size` bytes."""
        fitting = [r for r in self.regions if r[0] // BANK_SIZE in banks and r[1] - r[0] >= size]
        if not fitting:
            raise BuildError(f"out of space for {size} bytes in banks {sorted(banks)}")
        region = min(fitting, key=lambda r: r[1] - r[0])
        offset = region[0]
        region[0] += size
        return offset

    def reserve(self, bank, size):
        return self.take(size, {bank})


def place_strings(prg, variants, free):
    """Largest first into the eight banks with the most room; patches pointer immediates."""
    bank_slots = [bank for bank, _ in free.by_bank().most_common(8)]
    capacity = sum(size for bank, size in free.by_bank().items() if bank in bank_slots)
    placements = {}
    for key, variant in sorted(variants.items(), key=lambda item: -len(item[1]["data"])):
        data = bytes(variant["data"]) + bytes([END])
        offset = free.take(len(data), set(bank_slots))
        prg[offset:offset + len(data)] = data
        bank = offset // BANK_SIZE
        pointer = (bank_slots.index(bank) << 13) | (offset % BANK_SIZE)
        for site in variant["sites"]:
            prg[site["prg_offset"] + 1] = pointer & 0xFF
            prg[site["prg_offset"] + 5] = pointer >> 8
        placements[key] = {"bank": bank, "prg_offset": offset, "pointer": pointer,
                           "length": len(data)}
    return bank_slots, placements, capacity


def write_table(path, pairs):
    lines = ["00=\\n", "01={NAME letter}", "02={V}", "03={PAGE}", "FF={END}"]
    for index, char in enumerate(fonts.FONT_CHARS):
        lines.append(f"{0x80 + index:02X}={char}")
    lines.append(f"{SPACE:02X}= ")
    lines.extend(f"{DIGIT_BASE + digit:02X}={digit}" for digit in range(10))
    lines.append(f"{COLON:02X}=:")
    reverse = {char_code(c): c for c in fonts.FONT_CHARS + " 0123456789:"}
    for code, (first, second) in zip(PAIR_CODES, pairs):
        lines.append(f"{code:02X}={reverse[first]}{reverse[second]}")
    path.write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", default="Press Start 2P")
    parser.add_argument("--english-credits", action="store_true",
                        help="redraw the staff credits in English (name readings are unconfirmed)")
    args = parser.parse_args()

    rom = ROM_PATH.read_bytes()
    header = rom[:HEADER]
    prg = bytearray(rom[HEADER:HEADER + PRG_SIZE])
    chr_data = bytearray(rom[HEADER + PRG_SIZE:])

    dump = json.loads((ROOT / "script" / "dialogue_jp.json").read_text())
    strings = [s for s in dump["strings"] if s["id"] not in NOT_TEXT]
    for string in strings:
        for site in string["sites"]:
            site["id"] = string["id"]
    english = load_translations()
    missing = [s["id"] for s in strings if s["id"] not in english]
    if missing:
        raise BuildError(f"untranslated strings: {missing}")

    check_engine_entries(prg)

    variants = compile_script(strings, english)
    keys = sorted(variants)
    pairs, compressed = choose_pairs([variants[key]["codes"] for key in keys])
    for key, data in zip(keys, compressed):
        variants[key]["data"] = data

    regions = [(s["prg_offset"], s["prg_offset"] + s["length"] + 1) for s in strings]
    regions += [tail for tail in (bank_tail_free(prg, bank) for bank in range(FIXED_BANK)) if tail]
    free_regions = merge_regions(regions)
    free = FreeSpace(prg, free_regions)

    def tiles_for(text):
        return [code_tile(char_code(char)) for char in text]

    glyphs = fonts.candidate(args.font)
    screen_report = screens.apply(prg, chr_data, tiles_for, free.reserve, glyphs)
    bank_slots, placements, capacity = place_strings(prg, variants, free)

    symbols, engine_spans, hooks = install_engine(prg, pairs, bank_slots)
    for bank, cpu, tokens in POWER_NAME_TABLES:
        for index, token in enumerate(tokens):
            offset = prg_offset(bank, cpu) + index * 4
            prg[offset:offset + 4] = bytes([token, VALUE_SKIP, VALUE_SKIP, VALUE_SKIP])

    panel_clear = widen_panel_clear(prg)
    box_clear = widen_box_clear(prg)
    install_font(chr_data, glyphs)
    install_title_font(chr_data, glyphs)
    screens.attract(chr_data)
    credits_report = None
    if args.english_credits:
        credits_report = {
            **credits.apply(prg, chr_data, tiles_for, free.reserve),
            "immediates": [credits.CODE_BANK * BANK_SIZE + offset
                           for offset in (credits.WHITE_BANK_IMMEDIATES
                                          + credits.PINK_BANK_IMMEDIATES)],
        }

    out_rom = header + bytes(prg) + bytes(chr_data)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "Mindseeker (English).nes").write_bytes(out_rom)
    (dist / "mindseeker_en.ips").write_bytes(make_ips(rom, out_rom))
    write_table(dist / "mindseeker_en.tbl", pairs)

    used = sum(p["length"] for p in placements.values())
    report = {
        "font": args.font,
        "bank_slots": bank_slots,
        "pairs": pairs,
        "hooks": hooks,
        "engine_spans": engine_spans,
        "symbols": {name: symbols[name] for name in (
            "set_8000", "pair_first", "pair_second", "text_banks", "words", "word_starts")},
        "free_regions": free_regions,
        "power_tables": [prg_offset(bank, cpu) for bank, cpu, _ in POWER_NAME_TABLES],
        "panel_clear": panel_clear,
        "box_clear": box_clear,
        "credits": credits_report,
        "text_capacity": capacity,
        "text_used": used,
        "placements": [
            {
                "id": key[0], "lead": key[1], **placements[key],
                "codes": variants[key]["codes"],
                "sites": [site["prg_offset"] for site in variants[key]["sites"]],
                "kind": site_kind(variants[key]["sites"][0]),
            }
            for key in keys
        ],
        "screens": screen_report,
    }
    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    (build_dir / "build_report.json").write_text(json.dumps(report, indent=1))
    raw_size = sum(len(variants[key]["codes"]) for key in keys)
    print(f"{len(keys)} strings, {raw_size} raw bytes -> {used} placed of {capacity} free; "
          f"{len(pairs)} pairs; {len(hooks)} bank hooks; banks {bank_slots}")


if __name__ == "__main__":
    try:
        main()
    except BuildError as error:
        sys.exit(f"build failed: {error}")
