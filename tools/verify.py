#!/usr/bin/env python3
"""Strict checks on the built ROM and patch. Exits non-zero if any check fails.

Reads the untouched ROM, dist/ and build/build_report.json; trusts the ROM bytes, not the report,
for anything the game itself will read (pointers, strings, pair tables).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build
import fonts
import ips

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_SHA1 = "9701830b9827b7fccaa7888452c27fdea43b38ed"
HEADER, BANK, PRG_SIZE = 16, 0x2000, 0x20000
FONT_BANKS = (0x06, 0x0E)
PROMPT_BANK = 0x47
# The ending's code and tile lists in PRG bank 0, and the kanji name art in CHR.
CREDITS_PRG = (0x0C00, 0x1518)
CREDITS_CHR_BANKS = range(0x73, 0x78)

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))


def fixed(prg, cpu, count):
    start = 15 * BANK + (cpu - 0xE000)
    return list(prg[start:start + count])


def simulate(codes, kind, name_runs_width):
    """Replay the engine on expanded codes. Returns a list of problems."""
    problems = []
    width = build.ONELINE_WIDTH if kind == "oneline" else build.LINE_WIDTH
    line, column, value_index = 1, 0, 0
    for index, code in enumerate(codes):
        if code == build.NEWLINE:
            if kind == "oneline":
                problems.append("newline in a one-liner")
            line += 1
            column = 0
            if line > build.PAGE_LINES:
                problems.append("more than 3 lines on a page")
        elif code == build.PAGE:
            if kind == "oneline":
                problems.append("page break in a one-liner")
            line, column = 1, 0
        elif code == build.NAME:
            column += 1
        elif code == build.VALUE:
            column += name_runs_width.get(value_index, 1)
            value_index += 1
        elif 0x80 <= code < 0xD0:
            column += 1
        else:
            problems.append(f"orphan control code ${code:02X} at {index}")
        if column > width:
            problems.append(f"line {line} is {column} cells wide (limit {width})")
            column = 0
    return problems


def check_credits(staff, prg, old_chr, chr_allowed):
    """English credits: their font banks were free, and each loader finds a whole list."""
    for bank in staff["chr_banks"]:
        chr_allowed.update(range(bank * 0x400, bank * 0x400 + 0x400))
    check("credits font banks were empty in the original",
          all(set(old_chr[bank * 0x400:bank * 0x400 + 0x400]) == {0xFF}
              for bank in staff["chr_banks"]))

    bad_credits = []
    for item in staff["lists"]:
        loader = item["loader"]
        pointer = prg[loader + 1] | (prg[loader + 5] << 8)
        end = item["prg_offset"]
        while prg[end] != 0xFF:
            end += 3 + prg[end + 2]
        if ((pointer & 0x1FFF) != item["prg_offset"] % BANK
                or end + 1 - item["prg_offset"] != item["length"]
                or end >= staff["span"][1]):
            bad_credits.append(item["prg_offset"])
    check("each credits loader points at a well-formed list inside the original list area",
          not bad_credits and len(staff["lists"]) == 8, str(bad_credits))


def main():
    original = (ROOT / "Mindseeker (Japan).nes").read_bytes()
    built = (ROOT / "dist" / "Mindseeker (English).nes").read_bytes()
    patch = (ROOT / "dist" / "mindseeker_en.ips").read_bytes()
    report = json.loads((ROOT / "build" / "build_report.json").read_text())
    dump = json.loads((ROOT / "script" / "dialogue_jp.json").read_text())
    japanese = {s["id"]: s for s in dump["strings"]}
    prg, old_prg = built[HEADER:HEADER + PRG_SIZE], original[HEADER:HEADER + PRG_SIZE]
    chr_data, old_chr = built[HEADER + PRG_SIZE:], original[HEADER + PRG_SIZE:]
    symbols = report["symbols"]

    check("original ROM is untouched (SHA-1)", hashlib.sha1(original).hexdigest() == ORIGINAL_SHA1)
    check("built ROM keeps size and header",
          len(built) == len(original) and built[:HEADER] == original[:HEADER])

    # --- IPS ---
    check("IPS applied to the original reproduces the built ROM byte for byte",
          ips.apply_ips(original, patch) == built)
    offsets = list(ips.records(patch))
    check("IPS has no record at offset 0x454F46 and none past the file end",
          all(o != ips.EOF_OFFSET and o + s <= len(built) and s > 0 for o, s in offsets),
          f"{len(offsets)} records")
    check("IPS ends with the EOF marker and nothing after it",
          patch[:5] == b"PATCH" and patch.endswith(b"EOF"))
    big_a = bytearray(ips.EOF_OFFSET + 0x100)
    big_b = bytearray(big_a)
    for position in (ips.EOF_OFFSET - 3, ips.EOF_OFFSET, ips.EOF_OFFSET + 1, ips.EOF_OFFSET + 40):
        big_b[position] = 0x5A
    edge = ips.make_ips(bytes(big_a), bytes(big_b))
    check("IPS writer handles a change at offset 0x454F46 (synthetic 4.5 MB test)",
          all(o != ips.EOF_OFFSET for o, _ in ips.records(edge))
          and ips.apply_ips(bytes(big_a), edge) == bytes(big_b))

    # --- engine and hooks ---
    pair_count = len(build.PAIR_CODES)
    pairs = list(zip(fixed(prg, symbols["pair_first"], pair_count),
                     fixed(prg, symbols["pair_second"], pair_count)))
    check("pair tables in the ROM match the build's pairs",
          pairs[:len(report["pairs"])] == [tuple(p) for p in report["pairs"]])
    slots = [value & 0x0F for value in fixed(prg, symbols["text_banks"], 8)]
    check("text bank table in the ROM matches",
          slots[:len(report["bank_slots"])] == report["bank_slots"])
    jsr = bytes([0x20, symbols["set_8000"] & 0xFF, symbols["set_8000"] >> 8])
    check("all 53 bank writes go through the shadow hook",
          len(report["hooks"]) == 53
          and all(prg[h:h + 3] == jsr and old_prg[h:h + 3] == b"\x8D\x00\xE0"
                  for h in report["hooks"]))
    raw_writes = [i for i in range(len(prg) - 2) if prg[i:i + 3] == b"\x8D\x00\xE0"]
    engine_offsets = [(15 * BANK + s - 0xE000, 15 * BANK + e - 0xE000)
                      for s, e in report["engine_spans"]]
    check("the only direct $E000 writes left are the engine's own three",
          len(raw_writes) == 3
          and all(any(s <= w < e for s, e in engine_offsets) for w in raw_writes))
    check("engine code sits entirely inside the old printers' space",
          all(any(low <= s and e <= high for low, high in build.ENGINE_REGIONS)
              for s, e in report["engine_spans"]))
    try:
        build.check_engine_entries(bytearray(old_prg))
        entries_ok = True
    except build.BuildError:
        entries_ok = False
    check("no outside code jumps into the replaced printers except at kept entry points",
          entries_ok)

    # --- strings and pointers ---
    free = [tuple(r) for r in report["free_regions"]]
    pointer_bytes = set()
    spans = []
    bad_pointers, bad_data, bad_layout, bad_tokens = [], [], [], []
    for placement in report["placements"]:
        start = placement["prg_offset"]
        codes = placement["codes"]
        for site in placement["sites"]:
            pointer_bytes.update((site + 1, site + 5))
            pointer = prg[site + 1] | (prg[site + 5] << 8)
            bank = slots[pointer >> 13]
            if (bank * BANK + (pointer & 0x1FFF) != start
                    or prg[site] != 0xA9
                    or prg[site + 4] != 0xA9):
                bad_pointers.append(placement["id"])

        end = prg.index(0xFF, start)
        if build.expand(prg[start:end], pairs) != codes or end + 1 - start != placement["length"]:
            bad_data.append(placement["id"])
        if start // BANK != end // BANK or not any(s <= start and end + 1 <= e for s, e in free):
            bad_data.append(placement["id"] + " (outside free space)")
        spans.append((start, end + 1))

        name_runs = build.POWER_NAME_RUNS.get(placement["id"], ())
        widths, value_index, text = {}, 0, japanese[placement["id"]]["text"]
        run = 0
        position = 0
        while position < len(text):
            if text.startswith("<V>", position):
                count = 0
                while text.startswith("<V>", position):
                    count += 1
                    position += 3
                if run in name_runs:
                    widths[value_index] = build.POWER_NAME_WIDTH
                    for extra in range(1, count):
                        widths[value_index + extra] = 0
                value_index += count
                run += 1
            else:
                position += 1

        problems = simulate(codes, placement["kind"], widths)
        if problems:
            bad_layout.append((placement["id"], problems[:2]))
        if codes.count(build.VALUE) != text.count("<V>") or codes.count(build.NAME) % 4:
            bad_tokens.append(placement["id"])

    check("every pointer resolves to the exact start of its string in the right bank",
          not bad_pointers, str(bad_pointers[:5]))
    check("every string in the ROM decodes back to its compiled text and sits in free space",
          not bad_data, str(bad_data[:5]))
    check("no line exceeds its box width or 3 lines per page; no orphan control codes",
          not bad_layout, str(bad_layout[:5]))
    check("run-time value slots match the Japanese; name letters come in fours",
          not bad_tokens, str(bad_tokens[:5]))

    lists = report["screens"]["panels"] + report["screens"]["messages"]
    for item in lists:
        spans.append((item["prg_offset"], item["prg_offset"] + item["length"]))
    ordered = sorted(spans)
    check("no two strings or tile lists overlap",
          all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), f"{len(ordered)} items")

    # --- nothing else changed ---
    allowed = set(pointer_bytes)
    for start, end in (free + engine_offsets
                       + [tuple(s) for s in report["screens"]["in_place_spans"]]):
        allowed.update(range(start, end))
    for hook in report["hooks"]:
        allowed.update(range(hook, hook + 3))
    allowed.add(report["panel_clear"])
    allowed.update(report["box_clear"])

    # Only present when the build was asked for English credits; the default keeps the kanji.
    staff = report["credits"]
    if staff:
        allowed.update(range(staff["span"][0], staff["span"][1]))
        allowed.update(staff["immediates"])
        for item in staff["lists"]:
            allowed.update((item["loader"] + 1, item["loader"] + 5))
    for table in report["power_tables"]:
        allowed.update(range(table, table + 12))
    for item in lists:
        allowed.update(range(item["old_span"][0], item["old_span"][1]))
        if item["moved"]:
            for site in item["moved"]["sites"]:
                allowed.update((site + 1, site + 5))

    stray = [i for i in range(PRG_SIZE) if prg[i] != old_prg[i] and i not in allowed]
    check("no PRG byte changed outside text, engine, hooks, pointers and menu lists", not stray,
          f"first stray: {stray[:5]}")

    chr_allowed = set()
    for bank in FONT_BANKS:
        chr_allowed.update(range(bank * 0x400, bank * 0x400 + 0x400))
    chr_allowed.update(range(PROMPT_BANK * 0x400, PROMPT_BANK * 0x400 + 960))
    chr_allowed.update(range(build.TITLE_FONT_BANK * 0x400, build.TITLE_FONT_BANK * 0x400 + 0x400))
    for bank in build.screens.ATTRACT_BANKS:
        chr_allowed.update(range(bank * 0x400, bank * 0x400 + 960))
    for start, end in report["screens"]["chr_spans"]:
        chr_allowed.update(range(start, end))

    stars_kept = all(
        chr_data[build.TITLE_FONT_BANK * 0x400 + i * 16:
                 build.TITLE_FONT_BANK * 0x400 + i * 16 + 16]
        == old_chr[build.TITLE_FONT_BANK * 0x400 + i * 16:
                   build.TITLE_FONT_BANK * 0x400 + i * 16 + 16]
        for i in build.screens.TITLE_STAR_INDEXES)
    star_cells = all(
        (chr_data[cell] in build.screens.STAR_TILES) == (old_chr[cell] in build.screens.STAR_TILES)
        and (chr_data[cell] == old_chr[cell] or old_chr[cell] not in build.screens.STAR_TILES)
        for bank in build.screens.ATTRACT_BANKS
        for cell in range(bank * 0x400, bank * 0x400 + 960))
    check("title starfield tiles and their cells are untouched by the attract text",
          stars_kept and star_cells)

    if staff:
        check_credits(staff, prg, old_chr, chr_allowed)
    else:
        check("staff credits are byte-identical to the original",
              prg[CREDITS_PRG[0]:CREDITS_PRG[1]] == old_prg[CREDITS_PRG[0]:CREDITS_PRG[1]]
              and all(chr_data[bank * 0x400:(bank + 1) * 0x400]
                      == old_chr[bank * 0x400:(bank + 1) * 0x400] for bank in CREDITS_CHR_BANKS))

    stray_chr = [i for i in range(len(chr_data))
                 if chr_data[i] != old_chr[i] and i not in chr_allowed]
    check("no CHR byte changed outside the font banks, credits font copies, prompt, attract "
          "and title screens",
          not stray_chr)

    glyphs = fonts.candidate(report["font"])
    check("font tiles in CHR match the chosen font",
          all(chr_data[bank * 0x400 + i * 16:bank * 0x400 + i * 16 + 16]
              == build.tile_bytes(glyphs[c])
              for bank in FONT_BANKS
              for i, c in enumerate(fonts.FONT_CHARS)))

    panel_right = max((address & 0x1F) + len(text) - 1 for item in report["screens"]["panels"]
                      for address, text in item["records"] if 0x20E0 <= address < 0x2200)
    clear_right = 22 + prg[report["panel_clear"]] - 1
    check("panel labels stay inside the columns the game clears", panel_right <= clear_right,
          f"labels reach column {panel_right}, clear reaches {clear_right}")

    translated = {p["id"] for p in report["placements"]}
    expected = {s["id"] for s in dump["strings"]} - build.NOT_TEXT
    check("every extracted dialogue string is translated and inserted", translated == expected,
          f"{len(translated)} of {len(expected)}")

    width = max(len(name) for name, _, _ in results)
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name:<{width}}  {detail}")
    failed = [name for name, passed, _ in results if not passed]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
