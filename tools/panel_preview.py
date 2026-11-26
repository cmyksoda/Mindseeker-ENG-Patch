#!/usr/bin/env python3
"""Screenshot panel menus by drawing their tile lists into the live command panel.

The menus live deep in the game, so this reads each list back from the built ROM and pokes its
tiles into the nametable while the first scene's panel is open. It shows fit and font exactly;
it does not prove the game's own code draws them.

usage: panel_preview.py BANK:OFFSET [BANK:OFFSET ...]   (hex, as in screens.PANEL_LISTS)
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesen_run

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "dist" / "Mindseeker (English).nes"
HEADER = 16
# Between two scripted A presses, while the first scene's INFO menu is open and idle.
PANEL_FRAME = 4440
PANEL_ROWS, PANEL_COLUMNS = range(7, 16), range(23, 30)
BLANK = 0x24
OPENING_INPUTS = (
    "300-304:start,400-404:down,440-444:a,520-524:down,560-564:a,700-704:a,760-764:a,"
    "800-804:a,840-844:a,880-884:a,960-964:down,1000-1004:a,"
    + ",".join(f"{f}-{f + 4}:a" for f in range(1300, 4700, 160)))


def list_writes(rom, prg_offset):
    writes, position = [], HEADER + prg_offset
    while rom[position] != 0xFF:
        address, count = (rom[position] << 8) | rom[position + 1], rom[position + 2]
        writes += [(address + i, rom[position + 3 + i]) for i in range(count)]
        position += 3 + count
    return writes


def main():
    rom = ROM.read_bytes()
    report = json.loads((ROOT / "build" / "build_report.json").read_text())
    panels = {(p["bank"], p["offset"]): p for p in report["screens"]["panels"]}
    for spec in sys.argv[1:]:
        bank, offset = (int(part, 16) for part in spec.split(":"))
        writes = [(0x2000 + row * 32 + column, BLANK)
                  for row in PANEL_ROWS for column in PANEL_COLUMNS]
        writes += list_writes(rom, panels[(bank, offset)]["prg_offset"])
        pokes = "\n".join(
            f"    emu.write(0x{a:04X}, 0x{v:02X}, emu.memType.nesPpuMemory)" for a, v in writes)
        lua = f"function ON_FRAME(frame)\n  if frame == {PANEL_FRAME} then\n{pokes}\n  end\nend\n"
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as handle:
            handle.write(lua)
        name = f"panel_{bank}_{offset:04X}"
        result = mesen_run.run(str(ROM), OPENING_INPUTS, str(PANEL_FRAME + 4), PANEL_FRAME + 6,
                               prefix=name, lua=handle.name)
        Path(handle.name).unlink()
        print(name, "exit", result.returncode)


if __name__ == "__main__":
    main()
