#!/usr/bin/env python3
"""Print a disassembly range densely: 'ADDR MNEMONIC OPERAND' joined several per line.

usage: dense.py ROM BANK CPU_BASE START END [PER_LINE]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dis6502 import BANK_SIZE, HEADER, disassemble


def main():
    rom = Path(sys.argv[1]).read_bytes()
    bank, base, start, end = (int(v, 16) for v in sys.argv[2:6])
    per_line = int(sys.argv[6]) if len(sys.argv) > 6 else 5
    data = rom[HEADER + bank * BANK_SIZE:HEADER + (bank + 1) * BANK_SIZE]
    items = []
    for line in disassemble(data, base, start, end):
        if not line:
            items.append(None)
            continue
        address, rest = line.split(":", 1)
        items.append(f"{address} {rest[11:].strip()}")
    row = []
    for item in items:
        if item is None:
            if row:
                print(" | ".join(row))
                row = []
            continue
        row.append(f"{item:<18}")
        if len(row) == per_line:
            print(" | ".join(row))
            row = []
    if row:
        print(" | ".join(row))


if __name__ == "__main__":
    main()
