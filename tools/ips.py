#!/usr/bin/env python3
"""Create and apply IPS patches.

usage: ips.py apply ORIGINAL PATCH OUTPUT
"""
import sys
from pathlib import Path

MAGIC = b"PATCH"
EOF_MARKER = b"EOF"
EOF_OFFSET = int.from_bytes(EOF_MARKER, "big")
MAX_RECORD = 0xFFFF
MAX_OFFSET = 0xFFFFFF
# Bridge unchanged gaps this short: a new record header costs 5 bytes.
MERGE_GAP = 5


def changed_runs(original, modified):
    runs, start, index = [], None, 0
    while index < len(modified):
        differs = index >= len(original) or original[index] != modified[index]
        if differs and start is None:
            start = index
        elif not differs and start is not None:
            gap_end = index
            while gap_end < len(modified) and gap_end - index < MERGE_GAP and (
                    gap_end < len(original) and original[gap_end] == modified[gap_end]):
                gap_end += 1
            if gap_end < len(modified) and gap_end - index < MERGE_GAP:
                index = gap_end
                continue
            runs.append((start, index))
            start = None
        index += 1
    if start is not None:
        runs.append((start, len(modified)))
    return runs


def make_ips(original, modified):
    if len(modified) < len(original):
        raise ValueError("IPS cannot shrink a file")
    if len(modified) > MAX_OFFSET + 1:
        raise ValueError("file too large for IPS")
    out = bytearray(MAGIC)
    for start, end in changed_runs(original, modified):
        while start < end:
            # An offset spelling "EOF" would end the patch early, so begin one byte sooner.
            if start == EOF_OFFSET:
                start -= 1
            size = min(MAX_RECORD, end - start)
            if start + size == EOF_OFFSET and start + size < end:
                size -= 1
            out += start.to_bytes(3, "big") + size.to_bytes(2, "big") + modified[start:start + size]
            start += size
    return bytes(out + EOF_MARKER)


def apply_ips(original, patch):
    if patch[:5] != MAGIC:
        raise ValueError("not an IPS patch")
    data = bytearray(original)
    position = 5
    while True:
        offset_bytes = patch[position:position + 3]
        if len(offset_bytes) < 3:
            raise ValueError("IPS patch ends without an EOF marker")
        if offset_bytes == EOF_MARKER:
            position += 3
            break
        offset = int.from_bytes(offset_bytes, "big")
        size = int.from_bytes(patch[position + 3:position + 5], "big")
        position += 5
        if size == 0:
            count = int.from_bytes(patch[position:position + 2], "big")
            chunk = patch[position + 2:position + 3] * count
            position += 3
        else:
            chunk = patch[position:position + size]
            position += size
        if offset + len(chunk) > len(data):
            data.extend(b"\x00" * (offset + len(chunk) - len(data)))
        data[offset:offset + len(chunk)] = chunk
    if position == len(patch) - 3:
        del data[int.from_bytes(patch[position:], "big"):]
    elif position != len(patch):
        raise ValueError("unexpected data after the IPS EOF marker")
    return bytes(data)


def records(patch):
    """Yield (offset, size) for every record, for verification."""
    position = 5
    while patch[position:position + 3] != EOF_MARKER:
        offset = int.from_bytes(patch[position:position + 3], "big")
        size = int.from_bytes(patch[position + 3:position + 5], "big")
        position += 5 + (3 if size == 0 else size)
        yield offset, size


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "apply":
        sys.exit(__doc__)
    result = apply_ips(Path(sys.argv[2]).read_bytes(), Path(sys.argv[3]).read_bytes())
    Path(sys.argv[4]).write_bytes(result)
