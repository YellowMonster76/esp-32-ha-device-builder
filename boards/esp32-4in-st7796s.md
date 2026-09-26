# 4" ESP32 display: 320×480, ST7796S, resistive touch

> **Status: ordered, not yet tested.** Everything below "Purchase" is what the
> listing claims, or what's likely, until checked on the real board. No board
> package (`.yaml`) yet: it gets written once the pins are confirmed on
> hardware.

## Purchase

| Where | Listing | Ordered | Price |
|---|---|---|---|
| AliExpress, Seablue 1618 Store | https://www.aliexpress.com/item/1005010532808949.html | **With touch** variant | £11.44 (at time of order, excl. £4.83 delivery) |

Listing title: *"4 inch ESP32 WiFi Bluetooth Development Board 320x480
Intelligent Display Module Onboard ESP32-WROOM-32E Module ST7796S Driver"*.
Variants offered: With touch / Without touch.

## What the listing says

- ESP32-WROOM-32E module (Wi-Fi 4, Bluetooth 4.2)
- 4.0" 320×480 display, ST7796S controller
- Resistive touch on the "With touch" version
- USB-C for power and data, 5 V output

Likely the same design as LCDwiki's "4.0inch ESP32-32E Display" (models
E32R40T with touch, E32N40T without). **Unconfirmed:** check the PCB markings.

## Expected differences from the CYD (to confirm)

- **Bigger screen, same class of chip.** A plain ESP32 with no PSRAM (the
  WROOM-32E has none). A full 320×480 16-bit framebuffer (300 KB) won't fit,
  so use LVGL with a partial buffer, as on the CYD (`buffer_size: 25%`,
  display `update_interval: never`).
- **ESPHome driver:** `mipi_spi` with `model: ST7796` (generic, 320×480
  portrait). There's no board preset for this one, so pins, `invert_colors`,
  `color_order` and orientation need setting and checking by hand.
- **Touch is probably an XPT2046,** like the CYD, but it may share the
  display's SPI bus instead of having its own. Check the pins.

## Arrival checklist

1. **PCB markings:** model number (E32R40T?), module marking, USB-serial
   chip (CH340? CP2102?).
2. **Chip and flash:** `python -m esptool --port COMx flash-id` for the chip
   revision, MAC and flash size.
3. **Factory firmware:** `python tools/serial_log.py COMx --reset --seconds 15`
   to see what it prints at boot (sometimes the display driver and pins).
4. **Pinout:** from the seller or LCDwiki docs, then confirm each on the
   board:
   - display SCK / MOSI / MISO / CS / DC / RST, backlight pin (dim it to be
     sure it's the backlight),
   - touch CS / IRQ, and whether it shares the display's SPI bus,
   - anything else on board: RGB LED (active low?), light sensor, speaker,
     SD slot, battery connector.
5. **Display:** start from the CYD's test-card approach
   ([`tools/touch-calibration`](../tools/touch-calibration/cyd-touch-calibration.yaml)
   shows the test card) with `model: ST7796` and this board's pins. Fix the
   colours (`invert_colors`, `color_order`) and orientation (LVGL `rotation`).
6. **Touch:** calibrate with `tools/touch-calibration` (update its pins) and
   note any `transform` needed with the chosen rotation.
7. **Then:** write `esp32-4in-st7796s.yaml` (board package), fill in the
   Pinout and Quirks sections here, and update the status line.

## Pinout

*To be confirmed on hardware.*

## Quirks found on the real hardware

*None yet.*
