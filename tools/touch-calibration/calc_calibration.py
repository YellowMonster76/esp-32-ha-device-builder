"""Turn logged corner taps into XPT2046 calibration values.

Input: a log with lines containing "raw_x=<n> raw_y=<n>" (from the board's
*-touch-calibration.yaml), taps in this order, holding the board as --board
describes: top-left, top-right, bottom-right, bottom-left, [centre].
The last 5 taps are used (4 if there are only 4), so stray taps at the start
are fine.

  python calc_calibration.py taps.log                     # CYD
  python calc_calibration.py taps.log --board esp32-4in   # 4" ST7796S
  python calc_calibration.py taps.log --inset-mm 5

The taps are about --inset-mm in from each edge, so the edge values are
extrapolated from them. Values are printed min < max, as ESPHome requires;
any axis flip is the board file's `transform`.
"""
import argparse
import re
import sys

# raw_h / raw_v: which raw reading (0 = raw_x, 1 = raw_y) follows the screen's
# horizontal / vertical axis when held as `hold` says.
BOARDS = {
    "cyd": dict(
        hold="landscape, USB sockets on the right",
        W=320, H=240,
        px_per_mm=320 / 57.6,    # 2.8" panel, active area ~57.6 x 43.2 mm
        raw_h=1, raw_v=0,        # raw Y left->right, raw X top->bottom
    ),
    "esp32-4in": dict(
        hold="portrait, USB socket at the bottom",
        W=320, H=480,
        px_per_mm=320 / 55.68,   # active area 55.68 x 83.52 mm (LCDwiki)
        raw_h=0, raw_v=1,        # raw X left->right, raw Y bottom->top
    ),
}

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("log", help="log file ('-' for stdin)")
p.add_argument("--board", choices=BOARDS, default="cyd")
p.add_argument("--inset-mm", type=float, default=5.0, help="how far in from the edges you tapped")
a = p.parse_args()
b = BOARDS[a.board]
W, H, h, v = b["W"], b["H"], b["raw_h"], b["raw_v"]
print(f"{a.board}: taps taken {b['hold']}")

text = sys.stdin.read() if a.log == "-" else open(a.log, encoding="utf-8").read()
taps = [(int(x), int(y)) for x, y in re.findall(r"raw_x=(\d+)\s+raw_y=(\d+)", text)]
if len(taps) < 4:
    sys.exit(f"need at least 4 taps, found {len(taps)}")
centre = None
if len(taps) >= 5:
    *corners, centre = taps[-5:]
else:
    corners = taps[-4:]
tl, tr, br, bl = corners
print(f"using  TL={tl}  TR={tr}  BR={br}  BL={bl}" + (f"  C={centre}" if centre else ""))

# sanity: the top pair should share their vertical reading, the left pair
# their horizontal one, and so on
for name, a1, a2 in [("top", tl[v], tr[v]), ("bottom", bl[v], br[v]),
                     ("left", tl[h], bl[h]), ("right", tr[h], br[h])]:
    if abs(a1 - a2) > 400:
        print(f"WARNING: {name} pair differs a lot ({a1} vs {a2}): wrong tap order or a stray tap?")

inset = a.inset_mm * b["px_per_mm"]


def edges(near, far, size):
    """Extrapolate the readings at 0 and `size` px from taps `inset` px in."""
    per_px = (far - near) / (size - 2 * inset)
    return near - inset * per_px, far + inset * per_px


left_e, right_e = edges((tl[h] + bl[h]) / 2, (tr[h] + br[h]) / 2, W)
top_e, bottom_e = edges((tl[v] + tr[v]) / 2, (bl[v] + br[v]) / 2, H)
cal = {h: sorted((left_e, right_e)), v: sorted((top_e, bottom_e))}

print("\nDevice file substitutions:")
for i, axis in enumerate("xy"):
    print(f'  touch_{axis}_min: "{round(cal[i][0])}"')
    print(f'  touch_{axis}_max: "{round(cal[i][1])}"')

if centre:
    px = (centre[h] - left_e) / (right_e - left_e) * W
    py = (centre[v] - top_e) / (bottom_e - top_e) * H
    print(f"\nCentre tap maps to ({px:.0f}, {py:.0f}); screen centre is ({W // 2}, {H // 2}).")
