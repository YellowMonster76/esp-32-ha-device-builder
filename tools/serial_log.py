"""Read an ESP32's serial log over USB, optionally filtered.

By default it opens the port WITHOUT resetting the board (DTR/RTS held off),
so you see what a running device is doing. Use --reset to restart it and
capture the boot log too.

  python tools/serial_log.py COM4                       # everything, until Ctrl+C
  python tools/serial_log.py COM4 --seconds 60 --grep "touch x=|Tapped"
  python tools/serial_log.py COM4 --reset --seconds 20 --out boot.log

Needs pyserial (pip install pyserial; it comes with esphome/esptool).
Only one program can have the port open: close this before flashing.
"""
import argparse
import re
import sys
import time

import serial

ANSI = re.compile(r"\x1b\[[0-9;]*m")

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("port", help="e.g. COM4 or /dev/ttyUSB0")
p.add_argument("--baud", type=int, default=115200)
p.add_argument("--seconds", type=float, default=0, help="stop after this long (0 = until Ctrl+C)")
p.add_argument("--grep", help="only lines matching this regex")
p.add_argument("--reset", action="store_true", help="reset the board on open (captures boot log)")
p.add_argument("--out", help="also append lines to this file")
a = p.parse_args()

s = serial.Serial()
s.port, s.baudrate, s.timeout = a.port, a.baud, 0.2
s.dtr = False   # set before open(), so the auto-reset circuit isn't triggered
s.rts = False
s.open()
if a.reset:
    # RTS alone pulls EN low; DTR stays off so GPIO0 is high (normal boot, not
    # the bootloader). Just opening the port asserts both, which on some
    # boards does nothing.
    s.rts = True
    time.sleep(0.1)
    s.rts = False
pat = re.compile(a.grep) if a.grep else None
out = open(a.out, "a", encoding="utf-8", buffering=1) if a.out else None
start, rest, count = time.time(), "", 0
try:
    while not a.seconds or time.time() - start < a.seconds:
        rest += s.read(4096).decode("utf-8", "replace")
        *lines, rest = rest.split("\n")
        for line in lines:
            line = ANSI.sub("", line).rstrip("\r")
            if pat and not pat.search(line):
                continue
            count += 1
            print(line, flush=True)
            if out:
                out.write(line + "\n")
except KeyboardInterrupt:
    pass
finally:
    s.close()
print(f"-- {count} line(s)", file=sys.stderr)
