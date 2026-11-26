#!/usr/bin/env python3
"""Minimal 6502 disassembler for 8K PRG banks of the Mindseeker ROM.

usage: dis6502.py ROM BANK CPU_BASE [START [END]]   (hex numbers)
"""
import sys
from pathlib import Path

HEADER = 16
BANK_SIZE = 0x2000

IMP, ACC, IMM, ZP, ZPX, ZPY, ABS, ABX, ABY, IND, IZX, IZY, REL = range(13)
LENGTH = {
    IMP: 1, ACC: 1, IMM: 2, ZP: 2, ZPX: 2, ZPY: 2, ABS: 3,
    ABX: 3, ABY: 3, IND: 3, IZX: 2, IZY: 2, REL: 2,
}

OPCODES = {}


def _add(name, entries):
    for code, mode in entries:
        OPCODES[code] = (name, mode)


_add("ADC", [(0x69, IMM), (0x65, ZP), (0x75, ZPX), (0x6D, ABS),
             (0x7D, ABX), (0x79, ABY), (0x61, IZX), (0x71, IZY)])
_add("AND", [(0x29, IMM), (0x25, ZP), (0x35, ZPX), (0x2D, ABS),
             (0x3D, ABX), (0x39, ABY), (0x21, IZX), (0x31, IZY)])
_add("ASL", [(0x0A, ACC), (0x06, ZP), (0x16, ZPX), (0x0E, ABS), (0x1E, ABX)])
_add("BIT", [(0x24, ZP), (0x2C, ABS)])
_add("CMP", [(0xC9, IMM), (0xC5, ZP), (0xD5, ZPX), (0xCD, ABS),
             (0xDD, ABX), (0xD9, ABY), (0xC1, IZX), (0xD1, IZY)])
_add("CPX", [(0xE0, IMM), (0xE4, ZP), (0xEC, ABS)])
_add("CPY", [(0xC0, IMM), (0xC4, ZP), (0xCC, ABS)])
_add("DEC", [(0xC6, ZP), (0xD6, ZPX), (0xCE, ABS), (0xDE, ABX)])
_add("EOR", [(0x49, IMM), (0x45, ZP), (0x55, ZPX), (0x4D, ABS),
             (0x5D, ABX), (0x59, ABY), (0x41, IZX), (0x51, IZY)])
_add("INC", [(0xE6, ZP), (0xF6, ZPX), (0xEE, ABS), (0xFE, ABX)])
_add("JMP", [(0x4C, ABS), (0x6C, IND)])
_add("JSR", [(0x20, ABS)])
_add("LDA", [(0xA9, IMM), (0xA5, ZP), (0xB5, ZPX), (0xAD, ABS),
             (0xBD, ABX), (0xB9, ABY), (0xA1, IZX), (0xB1, IZY)])
_add("LDX", [(0xA2, IMM), (0xA6, ZP), (0xB6, ZPY), (0xAE, ABS), (0xBE, ABY)])
_add("LDY", [(0xA0, IMM), (0xA4, ZP), (0xB4, ZPX), (0xAC, ABS), (0xBC, ABX)])
_add("LSR", [(0x4A, ACC), (0x46, ZP), (0x56, ZPX), (0x4E, ABS), (0x5E, ABX)])
_add("ORA", [(0x09, IMM), (0x05, ZP), (0x15, ZPX), (0x0D, ABS),
             (0x1D, ABX), (0x19, ABY), (0x01, IZX), (0x11, IZY)])
_add("ROL", [(0x2A, ACC), (0x26, ZP), (0x36, ZPX), (0x2E, ABS), (0x3E, ABX)])
_add("ROR", [(0x6A, ACC), (0x66, ZP), (0x76, ZPX), (0x6E, ABS), (0x7E, ABX)])
_add("SBC", [(0xE9, IMM), (0xE5, ZP), (0xF5, ZPX), (0xED, ABS),
             (0xFD, ABX), (0xF9, ABY), (0xE1, IZX), (0xF1, IZY)])
_add("STA", [(0x85, ZP), (0x95, ZPX), (0x8D, ABS), (0x9D, ABX),
             (0x99, ABY), (0x81, IZX), (0x91, IZY)])
_add("STX", [(0x86, ZP), (0x96, ZPY), (0x8E, ABS)])
_add("STY", [(0x84, ZP), (0x94, ZPX), (0x8C, ABS)])
for _name, _code in [
    ("BPL", 0x10), ("BMI", 0x30), ("BVC", 0x50), ("BVS", 0x70),
    ("BCC", 0x90), ("BCS", 0xB0), ("BNE", 0xD0), ("BEQ", 0xF0),
]:
    OPCODES[_code] = (_name, REL)
for _name, _code in [
    ("BRK", 0x00), ("CLC", 0x18), ("CLD", 0xD8), ("CLI", 0x58), ("CLV", 0xB8),
    ("DEX", 0xCA), ("DEY", 0x88), ("INX", 0xE8), ("INY", 0xC8), ("NOP", 0xEA),
    ("PHA", 0x48), ("PHP", 0x08), ("PLA", 0x68), ("PLP", 0x28), ("RTI", 0x40),
    ("RTS", 0x60), ("SEC", 0x38), ("SED", 0xF8), ("SEI", 0x78), ("TAX", 0xAA),
    ("TAY", 0xA8), ("TSX", 0xBA), ("TXA", 0x8A), ("TXS", 0x9A), ("TYA", 0x98),
]:
    OPCODES[_code] = (_name, IMP)


def format_operand(mode, data, pc):
    if mode == IMP:
        return ""
    if mode == ACC:
        return "A"
    if mode == IMM:
        return f"#${data[0]:02X}"
    if mode == ZP:
        return f"${data[0]:02X}"
    if mode == ZPX:
        return f"${data[0]:02X},X"
    if mode == ZPY:
        return f"${data[0]:02X},Y"
    if mode == IZX:
        return f"(${data[0]:02X},X)"
    if mode == IZY:
        return f"(${data[0]:02X}),Y"
    if mode == REL:
        offset = data[0] - 256 if data[0] >= 128 else data[0]
        return f"${(pc + 2 + offset) & 0xFFFF:04X}"
    word = data[0] | (data[1] << 8)
    suffix = {ABS: "", ABX: ",X", ABY: ",Y"}.get(mode)
    if mode == IND:
        return f"(${word:04X})"
    return f"${word:04X}{suffix}"


def disassemble(bank_data, cpu_base, start, end):
    lines = []
    pc = start
    while pc < end:
        offset = pc - cpu_base
        opcode = bank_data[offset]
        if opcode not in OPCODES:
            lines.append(f"{pc:04X}: {opcode:02X}        .db ${opcode:02X}")
            pc += 1
            continue
        name, mode = OPCODES[opcode]
        length = LENGTH[mode]
        raw = bank_data[offset:offset + length]
        if len(raw) < length:
            break
        operand = format_operand(mode, raw[1:], pc)
        hex_bytes = " ".join(f"{b:02X}" for b in raw)
        lines.append(f"{pc:04X}: {hex_bytes:<9} {name} {operand}".rstrip())
        if name in ("RTS", "RTI", "JMP"):
            lines.append("")
        pc += length
    return lines


def main():
    rom = Path(sys.argv[1]).read_bytes()
    bank = int(sys.argv[2], 16)
    cpu_base = int(sys.argv[3], 16)
    start = int(sys.argv[4], 16) if len(sys.argv) > 4 else cpu_base
    end = int(sys.argv[5], 16) if len(sys.argv) > 5 else cpu_base + BANK_SIZE
    bank_data = rom[HEADER + bank * BANK_SIZE:HEADER + (bank + 1) * BANK_SIZE]
    print("\n".join(disassemble(bank_data, cpu_base, start, end)))


if __name__ == "__main__":
    main()
