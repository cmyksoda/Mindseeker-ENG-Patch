-- Log data reads from PRG ROM ($8000-$FFFF) within a frame window: frame pc cpu_addr rom_offset value
TRACE_FROM = TRACE_FROM or 440
TRACE_TO = TRACE_TO or 520
emu.addMemoryCallback(function(addr, value)
  local f = FRAME()
  if f >= TRACE_FROM and f <= TRACE_TO then
    local st = emu.getState()
    local c = emu.convertAddress(addr, emu.memType.nesMemory, emu.cpuType.nes)
    LOG(string.format("%d %04X %04X %05X %02X",
        f, st["cpu.pc"], addr, c and c.address or -1, value))
  end
end, emu.callbackType.read, 0x8000, 0xFFFF)
