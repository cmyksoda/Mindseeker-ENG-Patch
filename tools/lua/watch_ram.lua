-- Count writes to candidate free RAM bytes after the reset clear.
local counts = {}
for _, a in ipairs({0x3A, 0xFB}) do
  counts[a] = 0
  emu.addMemoryCallback(function(addr, value)
    if FRAME() > 5 then counts[a] = counts[a] + 1 end
  end, emu.callbackType.write, a, a)
end
function ON_END()
  for a, n in pairs(counts) do
    LOG(string.format("%02X writes=%d value=%02X",
        a, n, emu.read(a, emu.memType.nesMemory)))
  end
end
