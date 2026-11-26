#!/usr/bin/env python3
"""Drive MesenCE headless: scripted inputs, screenshots, optional extra Lua.

usage: mesen_run.py ROM --inputs "400-405:start,700-702:a" --shots 600,900 --end 1000
                        [--every N] [--prefix name] [--lua extra.lua] [--log out.txt]
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MESEN_DIR = ROOT / "project-data" / "mesen"
SHOT_DIR = ROOT / "project-data" / "shots"
# Mesen's test runner stops a run after about 100 s unless told otherwise.
TESTRUNNER_SECONDS = 900

LUA_TEMPLATE = r"""
local SHOT_DIR = "%(shot_dir)s/"
local PREFIX = "%(prefix)s"
local LOG_PATH = "%(log_path)s"
local END_FRAME = %(end_frame)d
local EVERY = %(every)d
local inputs = { %(inputs)s }
local shots = { %(shots)s }
local frame = 0
local log_file = nil
if LOG_PATH ~= "" then log_file = io.open(LOG_PATH, "w") end
function LOG(s) if log_file then log_file:write(s .. "\n") end end
function FRAME() return frame end
function SHOT(name)
  local h = io.open(SHOT_DIR .. name .. ".png", "wb")
  h:write(emu.takeScreenshot()) h:close()
end
%(extra)s
emu.addEventCallback(function()
  local pad = {}
  for _, e in ipairs(inputs) do
    if frame >= e[1] and frame <= e[2] then pad[e[3]] = true end
  end
  emu.setInput(pad, 0)
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  frame = frame + 1
  if shots[frame] or (EVERY > 0 and frame %% EVERY == 0) then
    SHOT(string.format("%%s_%%05d", PREFIX, frame))
  end
  if ON_FRAME then ON_FRAME(frame) end
  if frame >= END_FRAME then
    if ON_END then ON_END() end
    if log_file then log_file:close() end
    emu.stop(0)
  end
end, emu.eventType.endFrame)
"""


def parse_inputs(text):
    entries = []
    for part in filter(None, text.split(",")):
        frames, button = part.split(":")
        first, _, last = frames.partition("-")
        entries.append(f'{{{int(first)}, {int(last or first)}, "{button}"}}')
    return ", ".join(entries)


def run(rom, inputs="", shots="", end=600, every=0, prefix="shot", lua=None, log="", timeout=600):
    extra = Path(lua).read_text() if lua else ""
    script = LUA_TEMPLATE % {
        "shot_dir": SHOT_DIR,
        "prefix": prefix,
        "log_path": str(Path(log).resolve()) if log else "",
        "end_frame": end,
        "every": every,
        "inputs": parse_inputs(inputs),
        "shots": ", ".join(f"[{int(s)}]=true" for s in filter(None, shots.split(","))),
        "extra": extra,
    }
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as handle:
        handle.write(script)
    try:
        result = subprocess.run(
            ["xvfb-run", "-a", "./Mesen", "--testrunner", f"--timeout={TESTRUNNER_SECONDS}",
             str(Path(rom).resolve()), handle.name],
            cwd=MESEN_DIR, timeout=timeout, capture_output=True, text=True,
        )
    finally:
        Path(handle.name).unlink()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rom")
    parser.add_argument("--inputs", default="")
    parser.add_argument("--shots", default="")
    parser.add_argument("--end", type=int, default=600)
    parser.add_argument("--every", type=int, default=0)
    parser.add_argument("--prefix", default="shot")
    parser.add_argument("--lua")
    parser.add_argument("--log", default="")
    args = parser.parse_args()
    result = run(args.rom, args.inputs, args.shots, args.end, args.every, args.prefix, args.lua,
                 args.log)
    print("exit", result.returncode)
    if result.stdout.strip():
        print(result.stdout[-2000:])
    if result.stderr.strip():
        print(result.stderr[-2000:])


if __name__ == "__main__":
    main()
