"""Turn logged corner taps into XPT2046 calibration values for the CYD.

Input: a log with lines containing "raw_x=<n> raw_y=<n>" (from
cyd-touch-calibration.yaml), taps in this order, with the USB sockets on the
right:  top-left, top-right, bottom-right, bottom-left, [centre].
The last 5 taps are used (4 if there are only 4), so stray taps at the start
are fine.

  python calc_calibration.py taps.log
  python calc_calibration.py taps.log --inset-mm 5

On the CYD in landscape (LVGL rotation 90), raw X runs top->bottom and raw Y
runs left->right. The taps are about --inset-mm in from each edge, so the
edge values are extrapolated from them.
"""
import argparse
import re
import sys

W, H = 320, 240          # landscape pixels
PX_PER_MM = 320 / 57.6   # 2.8" panel, active area ~57.6 x 43.2 mm

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("log", help="log file ('-' for stdin)")
p.add_argument("--inset-mm", type=float, default=5.0, help="how far in from the edges you tapped")
a = p.parse_args()

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

# sanity: the top pair should share raw_x, the left pair raw_y, and so on
for name, a1, a2 in [("top raw_x", tl[0], tr[0]), ("bottom raw_x", bl[0], br[0]),
                     ("left raw_y", tl[1], bl[1]), ("right raw_y", tr[1], br[1])]:
    if abs(a1 - a2) > 400:
        print(f"WARNING: {name} differs a lot ({a1} vs {a2}): wrong tap order or a stray tap?")

inset = a.inset_mm * PX_PER_MM
top, bottom = (tl[0] + tr[0]) / 2, (bl[0] + br[0]) / 2
left, right = (tl[1] + bl[1]) / 2, (tr[1] + br[1]) / 2
sx = (bottom - top) / (H - 2 * inset)    # raw per pixel, vertical
sy = (right - left) / (W - 2 * inset)    # raw per pixel, horizontal
x_min, x_max = top - inset * sx, top + (H - inset) * sx
y_min, y_max = left - inset * sy, left + (W - inset) * sy

print("\nDevice file substitutions:")
print(f'  touch_x_min: "{round(x_min)}"')
print(f'  touch_x_max: "{round(x_max)}"')
print(f'  touch_y_min: "{round(y_min)}"')
print(f'  touch_y_max: "{round(y_max)}"')

if centre:
    px = (centre[1] - y_min) / (y_max - y_min) * W
    py = (centre[0] - x_min) / (x_max - x_min) * H
    print(f"\nCentre tap maps to ({px:.0f}, {py:.0f}); screen centre is (160, 120).")
