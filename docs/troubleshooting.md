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
| `serial_log.py --reset` captures nothing, not even the boot banner | Older versions opened the port with DTR and RTS both asserted, which doesn't reset every board (it didn't reset the 4" ST7796S). Fixed: it now pulses RTS alone, as esptool does. |

## Pairing and Home Assistant

| Symptom | Cause / fix |
|---|---|
| Device Builder says **Online** but the device shows "NO HA" or a "not connected" banner | "Online" only means it's on the network. Pair it: **Settings → Devices & services → Discovered → Configure**, and paste the API key from `secrets.yaml` if asked. |
| Music Assistant: playing on one speaker plays on a whole group | The speaker belongs to a group that's stopped but still **on**. Switch the group off (`media_player.turn_off`), not just stop it. |
| Music Assistant: a sync group of Google speakers plays on one only | Use a native Google speaker group (Google Home app) through its MA player instead. |
| Music Assistant: radio plays, albums don't ("Failed to cast media http://…:8097/…flac") | MA ↔ cast speaker stream problem, not the ESPHome device. Try MP3 output codec for the speaker in MA; check the speaker can reach MA's stream server. |
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
| "y_min must be smaller than y_max" (or x) in `calibration:` | That raw axis runs the opposite way to the screen. Keep min < max and flip it with `transform: mirror_y: true` (or `mirror_x`). The 4" ST7796S board needs `mirror_y`. |
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
- **Reading an HA action's answer:** `homeassistant.action` with
  `capture_response: true` and `on_success` (the lambda gets `response`). HA
  wraps it as `{"response": ...}`. Add a `response_template` to shrink big
  answers in HA before they're sent (the music panel does this).
- An action sent before HA has subscribed (right at connection) is **dropped**
  with a warning, and its `on_success` never runs. Delay a couple of seconds
  after `on_client_connected`.
- ESPHome **strips `//` comments from lambdas** and doesn't recognise C++ raw
  strings, so a `//` inside `R"(...)"` gets cut. Keep `//` out of literal
  strings in lambdas.
- LVGL **flex layout** can't be declared on a container with no widgets, and
  isn't compiled in unless some YAML uses it: position runtime-made widgets
  yourself.
- `!extend` on a script **adds** its steps after the original ones; it doesn't
  replace them.
