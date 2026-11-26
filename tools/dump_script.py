#!/usr/bin/env python3
"""Find every dialogue pointer site in the original ROM and dump the strings they reach.

Writes script/dialogue_jp.json: one entry per distinct string (bank, cpu address, ROM offset,
raw bytes, decoded text, and every call site that loads its pointer).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jp_table import build_script_table, decode

ROOT = Path(__file__).resolve().parent.parent
ROM_PATH = ROOT / "Mindseeker (Japan).nes"
HEADER = 16
BANK_SIZE = 0x2000
PRG_SIZE = 0x20000

# Banks that can sit in each CPU window while code from a given bank runs.
WINDOW_BANKS = {
    0: {0x8: [7], 0xA: [0], 0xC: [14]},
    1: {0x8: [1], 0xA: [5], 0xC: [6]},
    2: {0x8: [10], 0xA: [2], 0xC: [14]},
    5: {0x8: [4, 1, 3], 0xA: [5], 0xC: [6]},
    6: {0x8: [4, 3, 7], 0xA: [5], 0xC: [6]},
    8: {0x8: [11], 0xA: [8], 0xC: [14]},
    9: {0x8: [10], 0xA: [9], 0xC: [14]},
    13: {0x8: [12, 7], 0xA: [13], 0xC: [14]},
    14: {0x8: [10, 12, 7], 0xA: [13, 2, 9, 0], 0xC: [14]},
    15: {0x8: list(range(15)), 0xA: list(range(15)), 0xC: [6, 14]},
}

TABLE = build_script_table()
VALID = set(TABLE) | {0x00, 0x01, 0x10, 0xF0}


# Pointer pairs the game loads text addresses into: $20/$21 directly, or $32/$33 (copied later).
POINTER_PAIRS = [(0x20, 0x21), (0x32, 0x33)]

# Sites where two banks both decode; settled by reading the surrounding code and text.
SITE_BANK_OVERRIDES = {
    5 * BANK_SIZE + 0x1817: 1,
    6 * BANK_SIZE + 0x181B: 4,
    15 * BANK_SIZE + 0x06DA: 7,
    15 * BANK_SIZE + 0x0718: 7,
}


def find_sites(prg):
    """Yield (prg_offset, pointer, zp) for every `LDA #lo / STA lo_zp / LDA #hi / STA hi_zp`."""
    for i in range(len(prg) - 8):
        if prg[i] != 0xA9 or prg[i + 2] != 0x85 or prg[i + 4] != 0xA9 or prg[i + 6] != 0x85:
            continue
        if (prg[i + 3], prg[i + 7]) in POINTER_PAIRS:
            yield i, prg[i + 1] | (prg[i + 5] << 8), prg[i + 3]


def string_span(prg, bank, pointer):
    """Return (start, end) PRG offsets of a valid string, end at its $FF, else None."""
    start = bank * BANK_SIZE + (pointer & 0x1FFF)
    limit = (bank + 1) * BANK_SIZE
    end = start
    while end < limit and prg[end] != 0xFF:
        if prg[end] not in VALID:
            return None
        end += 1
    if end >= limit or end == start:
        return None
    return start, end


def resolve(prg, site, pointer):
    code_bank = site // BANK_SIZE
    if pointer < 0x8000:
        return None
    if pointer >= 0xE000:
        candidates = [15]
    else:
        candidates = WINDOW_BANKS.get(code_bank, {}).get((pointer >> 12) & 0xE, [])
    if site in SITE_BANK_OVERRIDES:
        candidates = [SITE_BANK_OVERRIDES[site]]
    spans = [(bank, string_span(prg, bank, pointer)) for bank in candidates]
    spans = [(bank, span) for bank, span in spans if span]
    if not spans:
        return None
    boundary = [(bank, span) for bank, span in spans if prg[span[0] - 1] == 0xFF]
    if len(boundary) == 1:
        return boundary[0]
    if len(spans) == 1:
        return spans[0]
    return ("ambiguous", spans)


def main():
    rom = ROM_PATH.read_bytes()
    prg = rom[HEADER:HEADER + PRG_SIZE]
    strings = {}
    rejected = []

    for site, pointer, zp in find_sites(prg):
        result = resolve(prg, site, pointer)
        if result is None or result[0] == "ambiguous":
            rejected.append({"site": site, "pointer": pointer,
                             "why": "ambiguous" if result else "no text"})
            continue
        bank, (start, end) = result
        entry = strings.setdefault(start, {
            "id": f"D{bank:02d}_{pointer:04X}",
            "bank": bank,
            "cpu": pointer,
            "prg_offset": start,
            "file_offset": start + HEADER,
            "length": end - start,
            "raw": prg[start:end].hex(),
            "text": decode(prg[start:end], TABLE),
            "boundary": prg[start - 1] == 0xFF,
            "sites": [],
        })
        entry["sites"].append({
            "prg_offset": site,
            "bank": site // BANK_SIZE,
            "zp": zp,
            "next": prg[site + 8:site + 11].hex(),
        })

    ordered = [strings[key] for key in sorted(strings)]
    out_dir = ROOT / "script"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "dialogue_jp.json").write_text(
        json.dumps({"strings": ordered, "rejected": rejected}, ensure_ascii=False, indent=1))
    print(f"{len(ordered)} strings, {sum(len(s['sites']) for s in ordered)} sites, "
          f"{len(rejected)} rejected")
    return ordered, rejected, prg


if __name__ == "__main__":
    main()
