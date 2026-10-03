# Project: light panel

Touch tiles that toggle Home Assistant lights and switches, with each tile
showing the entity's real state. One file per screen size; they behave the
same:

| File | Screen | Tiles | Used by |
|---|---|---|---|
| [`light-panel.yaml`](light-panel.yaml) | 320×240 landscape (CYD) | 8 (4 × 2) | [`cyd-light-panel-8tile`](../../cyd-light-panel-8tile.yaml) |
| [`light-panel-480x320.yaml`](light-panel-480x320.yaml) | 480×320 landscape (4" ST7796S) | 12 (4 × 3) | [`esp32-4in-light-panel-12tile`](../../esp32-4in-light-panel-12tile.yaml) (example entities), [demo](../../tools/demo/esp32-4in-light-panel-demo.yaml) |

**Needs from the board:** an LVGL display `tft` of that size, a
**calibrated** touchscreen `touch`, light `backlight`.

> Both files are **generated**. Edit
> [`tools/gen_light_panel.py`](tools/gen_light_panel.py) or
> [`tools/icon_set.py`](tools/icon_set.py), then run
> `python projects/light-panel/tools/gen_light_panel.py`.
> Changing which entities, names and icons a panel shows doesn't need the
> generator: that's in the device file. Add `--demo` to also regenerate the
> [demo build](../../tools/README.md#demo)'s project.

## Behaviour

| Tile | Meaning |
|---|---|
| amber | on |
| dark | off |
| faded, red edge | HA reports the entity unavailable (tap does nothing) |

- A tap sends `homeassistant.toggle`, so it works for lights, switches, fans
  and anything else that toggles. The tile changes only when HA reports the
  new state, so it can't show a state that didn't happen.
- The entity's state must be `on` or `off`. Anything else shows as
  unavailable, so **media players don't suit** (they report `playing`,
  `idle`...): use their power switch or smart plug instead.
- A red **"Not connected to Home Assistant"** banner appears when the API
  link drops.
- The screen goes **off after "Screen timeout"** (number in HA, 10–600 s,
  default 60). While it's off, LVGL is paused, so **the first tap only wakes
  it** and can't toggle anything by accident.
- The **Backlight** light in HA sets the brightness while awake.

## Home Assistant side: required

In **Settings → Devices & services → ESPHome**, open the panel's entry, click
**Configure**, and tick **"Allow the device to perform Home Assistant
actions"**. Without it, tiles show state but taps do nothing (the tile only
flashes grey).

## Setting the tiles (device file)

Three substitutions per tile, numbered left to right along each row, top row
first: on the CYD `b1`–`b4` top and `b5`–`b8` bottom; on the 4" panel
`b1`–`b4` top, `b5`–`b8` middle, `b9`–`b12` bottom.

```yaml
  b5_entity: light.kitchen_light
  b5_name: "Kitchen"             # about 9 characters max (13 on the 4" panel)
  b5_icon: "\U000F04DE"          # mdi:stove
```

`bN_icon` must be one of the **100 icons built into the font**. They're listed
with names under `font:` in `light-panel.yaml` (grouped: lights, rooms, audio
and TV, heating and air, appliances, power, security). Tiles can share icons.
An icon that's not in the set shows as a blank tile. To add one, put its
`(name, codepoint)` in `tools/icon_set.py` (browse at
https://pictogrammers.com/library/mdi/) and regenerate. Each icon can appear
only once, or ESPHome fails with "Found duplicate glyphs".

## Layout

| Layout | Tile size | Columns at x | Rows at y |
|---|---|---|---|
| 320×240 | 75 × 114 px | 4, 83, 162, 241 | 4, 122 |
| 480×320 | 115 × 101 px | 4, 123, 242, 361 | 4, 109, 214 |

4 px gaps. Icons are 56 px MDI, names 16 px Roboto, the same on both: the
two screens have about the same pixel density, so they look the same size.
Tile sizes live in the generator's `LAYOUTS` table; adding a screen size is a
new entry there.

## Tested

- **320×240 (CYD):** on the real board with HA: every tile toggles its entity and follows its state.
- **480×320 (4" ST7796S):** demo build on the real board, 2026-10-03. All 12
  tiles toggled under the finger, names up to 13 characters fit ("Bedroom
  heater" is cut off with "…"), and the screen timeout and wake-only first tap
  work. **Not yet run with HA**: the device file
  [`esp32-4in-light-panel-12tile`](../../esp32-4in-light-panel-12tile.yaml)
  has made-up example entities. Swap in your own before installing.
