#!/usr/bin/env python3
"""Tiny two-pass 6502 assembler: labels, `.org`, `.db`, `NAME = value`, and expressions.

Operands may use labels, `$hex`, decimal, `<expr` / `>expr` (low/high byte) and + or -.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dis6502 import ABS, ABX, ABY, ACC, IMM, IMP, IND, IZX, IZY, OPCODES, REL, ZP, ZPX, ZPY

ENCODE = {(name, mode): code for code, (name, mode) in OPCODES.items()}
BRANCHES = {name for (name, mode) in ENCODE if mode == REL}


class AsmError(Exception):
    pass


def evaluate(expr, symbols, strict):
    expr = expr.strip()
    if expr.startswith("<"):
        return evaluate(expr[1:], symbols, strict) & 0xFF
    if expr.startswith(">"):
        return (evaluate(expr[1:], symbols, strict) >> 8) & 0xFF
    total, sign = 0, 1
    for token in re.findall(r"[+-]|[^+-]+", expr):
        token = token.strip()
        if token == "+":
            sign = 1
        elif token == "-":
            sign = -1
        elif token.startswith("$"):
            total += sign * int(token[1:], 16)
        elif token.isdigit():
            total += sign * int(token)
        elif token in symbols:
            total += sign * symbols[token]
        elif strict:
            raise AsmError(f"unknown symbol {token!r}")
        else:
            total += 0x1000
    return total


def parse_operand(mnemonic, operand, symbols, strict, constants=()):
    """Return (mode, value)."""
    if not operand:
        return IMP, None
    if operand.upper() == "A":
        return ACC, None
    if operand.startswith("#"):
        return IMM, evaluate(operand[1:], symbols, strict)
    match = re.fullmatch(r"\((.+),\s*[xX]\)", operand)
    if match:
        return IZX, evaluate(match.group(1), symbols, strict)
    match = re.fullmatch(r"\((.+)\),\s*[yY]", operand)
    if match:
        return IZY, evaluate(match.group(1), symbols, strict)
    match = re.fullmatch(r"\((.+)\)", operand)
    if match:
        return IND, evaluate(match.group(1), symbols, strict)
    index = None
    match = re.fullmatch(r"(.+),\s*([xXyY])", operand)
    if match:
        operand, index = match.group(1), match.group(2).upper()
    value = evaluate(operand, symbols, strict)
    if mnemonic in BRANCHES:
        return REL, value
    name = operand.strip()
    # Labels keep absolute size so both passes agree; `NAME = value` constants may be zero page.
    zero_page = value < 0x100 and (not name.lstrip("<>")[0].isalpha() or name in constants)
    if index == "X":
        return (ZPX if zero_page and (mnemonic, ZPX) in ENCODE else ABX), value
    if index == "Y":
        return (ZPY if zero_page and (mnemonic, ZPY) in ENCODE else ABY), value
    return (ZP if zero_page and (mnemonic, ZP) in ENCODE else ABS), value


def assemble(source, symbols=None):
    """Assemble source text. Returns ({address: bytes} chunks, symbols)."""
    symbols = dict(symbols or {})
    constants = set(symbols)
    for strict in (False, True):
        chunks, pc, start, current = {}, None, None, bytearray()
        for raw in source.splitlines():
            line = raw.split(";")[0].strip()
            if not line:
                continue
            match = re.fullmatch(r"(\w+)\s*=\s*(.+)", line)
            if match:
                symbols[match.group(1)] = evaluate(match.group(2), symbols, strict)
                constants.add(match.group(1))
                continue

            match = re.match(r"(\w+):\s*(.*)", line)
            if match:
                symbols[match.group(1)] = pc
                line = match.group(2)
                if not line:
                    continue

            if line.startswith(".org"):
                if current:
                    chunks[start] = bytes(current)
                pc = start = evaluate(line[4:], symbols, strict)
                current = bytearray()
                continue
            if line.startswith(".db"):
                values = [evaluate(v, symbols, strict) & 0xFF for v in line[3:].split(",")]
                current.extend(values)
                pc += len(values)
                continue

            parts = line.split(None, 1)
            mnemonic = parts[0].upper()
            mode, value = parse_operand(
                mnemonic, parts[1].strip() if len(parts) > 1 else "", symbols, strict, constants)
            if (mnemonic, mode) not in ENCODE:
                raise AsmError(f"bad instruction: {raw!r}")
            current.append(ENCODE[(mnemonic, mode)])

            if mode == REL:
                offset = value - (pc + 2)
                if strict and not -128 <= offset <= 127:
                    raise AsmError(f"branch out of range: {raw!r}")
                current.append(offset & 0xFF)
                pc += 2
            elif mode in (IMM, ZP, ZPX, ZPY, IZX, IZY):
                if strict and not 0 <= value <= 0xFF:
                    raise AsmError(f"value out of range: {raw!r}")
                current.append(value & 0xFF)
                pc += 2
            elif mode in (ABS, ABX, ABY, IND):
                current.extend((value & 0xFF, (value >> 8) & 0xFF))
                pc += 3
            else:
                pc += 1
        if current:
            chunks[start] = bytes(current)
    return chunks, symbols
