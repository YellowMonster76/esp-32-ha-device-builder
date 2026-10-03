# 4" ESP32 display: 320×480, ST7796S, resistive touch

Package: [`esp32-4in-st7796s.yaml`](esp32-4in-st7796s.yaml)

> **Status: tested** on one unit (display, touch, backlight, RGB LED, BOOT
> button). Not tested yet: SD card, speaker, battery input. No device or
> project uses it yet.

- PCB marked **"ESP32-32E 320x480 resistance touch 4.0" LCD Display"**;
  module marked **ESP32-32E N4**
- ESP32-D0WD-V3 (rev 3.1), 4 MB flash, **no PSRAM**
- 4.0" 320×480 SPI TFT, ST7796S
- XPT2046 resistive touch, **sharing the display's SPI bus**
- CH340 USB-serial (shows up as `USB-SERIAL CH340`), USB-C
- RGB LED, SD slot, speaker connector, battery connector (not used here)

It matches LCDwiki's [4.0inch ESP32-32E Display](https://www.lcdwiki.com/4.0inch_ESP32-32E_Display)
(models E32R40T / E32N40T), and that page's pinout was right for every pin
checked. The model number isn't printed on our board.

## Purchase

| Where | Listing | What arrived |
|---|---|---|
| AliExpress, Seablue 1618 Store | https://www.aliexpress.com/item/1005010532808949.html | **With touch** variant, as above. £11.44 + £4.83 delivery at the time |

Listing title: *"4 inch ESP32 WiFi Bluetooth Development Board 320x480
Intelligent Display Module Onboard ESP32-WROOM-32E Module ST7796S Driver"*.
Variants offered: With touch / Without touch. The module is marked
"ESP32-32E", not "WROOM-32E".

**Factory firmware:** an Arduino LVGL v8 "Widgets demo" plus an SD card test.
It prints nothing on the serial port after the ROM boot banner. Back it up
before the first flash if you might want it back:
`python -m esptool --port COMx read-flash 0 0x400000 factory.bin`.

## Pinout

| Function | Pin | Checked | Notes |
|---|---|---|---|
| TFT SCLK / MOSI / MISO | 14 / 13 / 12 | yes | GPIO12 is a strapping pin (harmless warning) |
| TFT CS / DC | 15 / 2 | yes | |
| TFT reset | EN | | tied to the ESP32's reset, so no `reset_pin` |
| TFT backlight | 27 | yes | PWM (ledc), active high |
| Touch CLK / MOSI / MISO | 14 / 13 / 12 | yes | **same bus as the display** |
| Touch CS / IRQ | 33 / 36 | yes | 36 is input-only |
| RGB LED R / G / B | 22 / 16 / 17 | yes | **active LOW** |
| BOOT button | 0 | yes | low when pressed |
| SD card CLK / MOSI / MISO / CS | 18 / 23 / 19 / 5 | no | its own SPI bus (LCDwiki) |
| Audio enable / DAC | 4 / 26 | no | enable is active low (LCDwiki) |
| Battery ADC | 34 | no | reads ~2.08 V on USB with no battery; meaning unknown |

"Checked" means seen working on our board: the display drew, touch
answered, the backlight dimmed, the LED showed the right colour, the button
logged. The rest is from LCDwiki only.

## Display

ESPHome has no preset for this board. The generic `mipi_spi` `model: ST7796`
works with its defaults: colours correct (BGR, no inversion), test card the
right way up in portrait. It runs at `data_rate: 40MHz` (the default is
10 MHz) with no visible errors.

## Orientation

| Hold it | LVGL `rotation` |
|---|---|
| Portrait, USB socket at the bottom | `0` |
| Landscape, USB socket on the right | `90` |

As on the CYD, set `rotation:` under `lvgl:`, not under `display:`. Touch
follows the LVGL rotation with no extra transform (both checked with a 3×3
button grid). That's unlike the CYD, which needs `mirror_x` at rotation 90.

## Calibrating touch

Use [`tools/touch-calibration/`](../tools/README.md#touch-calibration):

1. Flash `esp32-4in-touch-calibration.yaml` (test card, logs raw touches).
2. Portrait, USB at the bottom: tap about 5 mm in from each corner, then the
   centre.
3. `calc_calibration.py taps.log --board esp32-4in` extrapolates to the edges
   and prints `touch_x_min/x_max` (raw X runs **left→right**) and
   `touch_y_min/y_max` (raw Y runs **bottom→top**) for the device file.
4. Check with `esp32-4in-touch-check.yaml`: each tap should hit the button
   under the finger.

Raw Y runs the opposite way to screen Y. ESPHome rejects `y_min > y_max`, so
the board file flips it with `transform: mirror_y: true`.

Measured on our unit: x 109–4034, y 140–3984. They're the board file's
defaults.

## Quirks found on the real hardware

- **Touch shares the display's SPI bus.** One `spi:` entry, two CS pins. The
  CYD has a separate touch bus, so its board file isn't a template for the
  bus setup.
- **`serial_log.py --reset` didn't reset this board** until it was changed
  to pulse RTS on its own. Opening the port asserts DTR and RTS together, and
  on this board's auto-reset circuit that leaves EN alone.
- **Memory:** no PSRAM, so a full 320×480 16-bit framebuffer (300 KB) can't
  fit. With LVGL, `mipi_spi` needs no framebuffer of its own, and LVGL's
  `buffer_size: 25%` works.
- Harmless boot warnings: GPIO12 and GPIO15 strapping pins.
