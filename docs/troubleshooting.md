# Troubleshooting

Problems we actually hit, and what fixed them. Board-specific hardware quirks
are in each board's notes (e.g. [CYD](../boards/cyd-2432s028.md)).

## Flashing

| Symptom | Cause / fix |
|---|---|
| "Plug into this computer" not offered or fails | The browser needs HA open over **https**, in Chrome or Edge. Plain `http://…:8123` blocks Web Serial. Otherwise use **Manual download → Factory format** and flash the `.bin` with esptool or web.esphome.io. |
| Flash stops midway ("Lost connection", then "Access is denied") | USB dropout, often from moving the board. Unplug, replug, retry. If it keeps happening, try another cable or port. |
| "Could not open COM4, the port is busy" | Something else has the port open (a serial monitor, another flash). Close it. |
| ESP-IDF install fails with "MSys/Mingw is not supported" (local builds) | Run `esphome` from PowerShell or cmd, not Git Bash. |
| Local build fails on long paths (Windows) | Build from a short path such as `C:\build`. |

## Pairing and Home Assistant

| Symptom | Cause / fix |
|---|---|
| Device Builder says **Online** but the device shows "NO HA" or a "not connected" banner | "Online" only means it's on the network. Pair it: **Settings → Devices & services → Discovered → Configure**, and paste the API key from `secrets.yaml` if asked. |
| Entity states show, but **taps/actions do nothing** | Tick **"Allow the device to perform Home Assistant actions"** in the device's ESPHome integration options. |
| Values stuck on `unknown` | Check the entity IDs in the YAML match HA exactly. Also: attributes arrive only if the entity exists and has that attribute. |
| Bool attributes don't match `"true"` | HA's ESPHome integration sends bool attributes as `on`/`off`. |
| Stale attribute values after an entity goes `unknown` | HA doesn't clear attributes. Decide "is there data" from the state, not the attributes. |

## Display and touch

| Symptom | Cause / fix |
|---|---|
| White, inverted or garbage screen | Wrong display controller for the board revision. Change the board's `display_model`. |
| "use of 'rotation' in the display config is not compatible with LVGL" | Set `rotation:` under `lvgl:`, not under `display:`. |
| Taps hit the mirror-image position (top ↔ bottom) | Touch transform: on the CYD with LVGL rotation 90, `mirror_x: true`. |
| Text wraps instead of truncating with "…" | LVGL `long_mode: DOT` only truncates when the label has a fixed `height`. |
| Big text overlapping other widgets | Measure the widest string it can show (e.g. "Due", "~25", "99+") and switch to a smaller font for it. |
| `pressed:` / `checked:` "invalid option for style_definitions" | State styles go on the widget itself, not in `style_definitions`. |
| "Found duplicate glyphs" | A font's `glyphs:` list contains the same character twice. List each icon once. |
| `request for member ... which is of pointer type` in a lambda | `id(x)` for lights and many components is a pointer: use `->`, not `.`. |
| Screen dark after a replug, and taps don't wake it | Backlight restored "off" at boot. Use `restore_mode: ALWAYS_ON`. |
| Night brightness looks like "off" | Gamma correction. Set `gamma_correct: 1.0` so percentages are real PWM duty. |

## ESPHome config gotchas (2026.9)

- `logger.log` defaults to **DEBUG** level. With `logger: level: INFO`, add
  `level: INFO` to see it.
- An `ota:` password is discouraged when the API uses encryption. Use
  `ota: - platform: esphome` with `encryption: {}` so it uses the API key.
- `xpt2046` requires a `calibration:` block even if touch targets don't matter.
- In packages, `!secret` names can't come from substitutions. That's why the
  API key and fallback hotspot are set in each device file.
