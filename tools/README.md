# Tools

Things used to bring up and check a board, kept so the next one is quicker.

## Local ESPHome

A Python venv with ESPHome **2026.9.0** (the same version as the HA add-on),
plus pyserial and PyYAML. `<venv>` below is wherever you put it (a short path,
e.g. `C:\esphome-venv`):

```bash
python -m venv <venv>
<venv>\Scripts\python.exe -m pip install esphome==2026.9.0 pyserial PyYAML
```

- Run `esphome` from **PowerShell or cmd, not Git Bash**. ESP-IDF refuses to
  install under MSYS.
- Keep the venv and build folders on **short paths**. A venv under a long path
  failed to create, and Windows path-length limits bite ESP-IDF builds too.
- The first compile downloads the ESP-IDF toolchain (several minutes). Later
  builds reuse it.
- Match the add-on's ESPHome version when you upgrade it, so local checks mean
  the same thing as Device Builder's.

The commands below use `esphome` and `python`. Either activate the venv
(`<venv>\Scripts\activate`) or use the full paths.

| Tool | What it's for |
|---|---|
| [`flatten.py`](flatten.py) | Build the paste-ready single files in `single-file/` from the device files |
| [`serial_log.py`](serial_log.py) | Read a board's USB log, filtered, **without resetting it** |
| [`compare_configs.py`](compare_configs.py) | Prove two configs merge to the same thing (after a refactor) |
| [`touch-calibration/`](touch-calibration/) | Firmware + calculator to calibrate a resistive touch panel |
| [`demo/`](demo/) | Run a project on a bare board with fake data: no Wi-Fi or HA |

## flatten.py

```bash
python tools/flatten.py              # all device files -> single-file/
python tools/flatten.py --check      # exit 1 if single-file/ is out of date
```

Merges each device file's packages (base, board, project) and its own
settings into one file, **as text, so comments are kept**. It follows
ESPHome's package rules: later settings win, `!extend` items fold into the
item they extend, and overridden values are marked "set in <file>". If it
meets something it can't merge cleanly, it stops with an error rather than
guessing.

Always confirm the result:

```bash
python tools/compare_configs.py cyd-bus-display.yaml single-file/cyd-bus-display.yaml
```

`single-file/` needs a `secrets.yaml` beside the files for that check (dummy
values are fine; it's git-ignored).

## serial_log.py

```bash
python tools/serial_log.py COM4 --seconds 60 --grep "touch x=|Tapped"
```

- By default it opens the port **without resetting** the board (DTR/RTS held
  off). Add `--reset` to restart it (an RTS pulse, as esptool does) and
  capture the boot log.
- `--out file.log` also saves the lines.
- Only one program can hold the port. Close it before flashing, or the upload
  fails with "port is busy".
- Remember `logger.log` defaults to DEBUG. With `logger: level: INFO`, log at
  INFO or you'll see nothing.

## compare_configs.py

```bash
set ESPHOME=<venv>\Scripts\esphome.exe
python tools/compare_configs.py old-single-file.yaml cyd-bus-display.yaml
```

Runs `esphome config` on both and compares the merged result as data, so
ordering doesn't matter. "IDENTICAL" means the firmware behaves the same.
This is how the split into board/project/device files was checked. Each file
needs a `secrets.yaml` beside it with the same secret names (dummy values are
fine).

## touch-calibration/

For resistive panels, which vary unit to unit. One firmware per board, with
full steps in its header:

| Board | Calibration firmware | `--board` | Hold it | Check with |
|---|---|---|---|---|
| CYD | [`cyd-touch-calibration.yaml`](touch-calibration/cyd-touch-calibration.yaml) | `cyd` (default) | landscape, USB on the right | the light-panel demo |
| 4" ST7796S | [`esp32-4in-touch-calibration.yaml`](touch-calibration/esp32-4in-touch-calibration.yaml) | `esp32-4in` | portrait, USB at the bottom | [`esp32-4in-touch-check.yaml`](touch-calibration/esp32-4in-touch-check.yaml) |

1. Flash it: test card on screen, no Wi-Fi.
2. Log taps with `serial_log.py ... --grep raw_x= --out taps.log`.
3. Tap near the four corners, then the centre.
4. `python tools/touch-calibration/calc_calibration.py taps.log --board <board>`
   prints the four `touch_*` substitutions and where the centre tap lands, as
   a check.

Then confirm: each tap should hit the tile or button under your finger. The
4" touch check is the real board package plus a 3×3 button grid that logs
`HIT <name>`.

## demo/

Ordinary device files that include the **real** board and project packages,
plus fake data. So a demo always shows the current project, not a copy of it.

| Demo | Shows |
|---|---|
| [`cyd-bus-display-demo.yaml`](demo/cyd-bus-display-demo.yaml) | Cycles 10 scenarios every 6 s: on time, late, very late, timetable-only, last bus, due, early, overnight (and night brightness), stale, HA lost |
| [`cyd-light-panel-demo.yaml`](demo/cyd-light-panel-demo.yaml) | 8 tiles that toggle locally, and every tap logged with its coordinates |

```bash
cd tools/demo
esphome run cyd-bus-display-demo.yaml --device COM4
```

How they fake things:
- **"HA connected":** projects read `${ha_connected}` (defined in
  `common/base.yaml`), and demos override it.
- **Data:** a demo `interval` calls `publish_state()` on the project's
  `homeassistant` sensors.
- **Clock:** `settimeofday()` in the demo lambda sets a fixed time.
- **Light panel:** `light-panel-demo.yaml` is generated alongside the real
  project by `gen_light_panel.py --demo`, with checkable tiles.
- **Secrets:** [`demo/secrets.yaml`](demo/secrets.yaml) holds **dummy**
  values and is committed on purpose. Wi-Fi fails to connect and the board
  falls back to its hotspot, which is fine for a demo.
