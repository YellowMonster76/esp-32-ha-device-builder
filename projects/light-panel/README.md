# Project: light panel

[`light-panel.yaml`](light-panel.yaml): 8 touch tiles (4 × 2) that toggle
Home Assistant lights and switches, with each tile showing the entity's
real state.

**Needs from the board:** a 320×240 landscape LVGL display `tft`, a
**calibrated** touchscreen `touch`, light `backlight`. Used by
[`cyd-light-panel`](../../cyd-light-panel.yaml).

> `light-panel.yaml` is **generated**. Edit
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

Three substitutions per tile. `b1`–`b4` are the top row left to right, and
`b5`–`b8` the bottom row:

```yaml
  b5_entity: light.kitchen_light
  b5_name: "Kitchen"             # about 9 characters max
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

Tiles are 75 × 114 px with 4 px gaps: columns at x = 4, 83, 162, 241 and rows
at y = 4, 122. Icons are 56 px MDI, names 16 px Roboto. Tile count and
positions live in the generator.
