# Project: bus display

The next bus from a stop, readable from about 2 m, with data pushed from Home
Assistant over the native API. A device includes **one layout plus
`brightness.yaml`**:

| File | What | Screen | Used by |
|---|---|---|---|
| [`bus-display.yaml`](bus-display.yaml) | layout: one stop | 320×240 landscape (CYD) | [`cyd-bus-display`](../../cyd-bus-display.yaml) |
| [`bus-display-2stop-480x320.yaml`](bus-display-2stop-480x320.yaml) | layout: two stops side by side | 480×320 landscape (4" ST7796S) | [`esp32-4in-bus-display-2stop`](../../esp32-4in-bus-display-2stop.yaml) (placeholder stops) |
| [`brightness.yaml`](brightness.yaml) | backlight behaviour, shared | any | both |

**Needs from the board:** an LVGL display `tft` of that size, touchscreen
`touch`, light `backlight`.

```yaml
packages:
  base: !include common/base.yaml
  board: !include boards/cyd-2432s028.yaml
  project: !include projects/bus-display/bus-display.yaml
  brightness: !include projects/bus-display/brightness.yaml
```

The single-stop screen:

```
+--------------------------------------------+
| HIGH STREET              [STALE] ● 19:42    |  header: status + clock
|                          +--------+        |
|   17                     |   S9   |        |  minutes to go (the big number)
|  min                     +--------+        |
|                            19:59           |  expected departure time
|                          [ On time ]       |  lateness chip
| to Wantage                                 |
| Then 20:29 S9                  LAST BUS    |  following bus / last bus tag
+--------------------------------------------+
```

## What it shows

- **Countdown:** minutes until the expected departure (scheduled + delay).
  Shows "Due" at 0 and "99+" above 99. Countdowns of 3 or more characters
  switch to a smaller font so they clear the route badge.
- **Live vs timetable:** a departure with `live: off` is a timetable guess.
  It shows as `~17` in grey, with a grey route badge, a grey time and a
  "Timetable" chip, so it never looks like tracked data.
- **Lateness chip** (from `delay`):

  | delay | chip |
  |---|---|
  | ≤ −2 | amber "N min early" (you could miss it) |
  | −1 … +1 | green "On time" |
  | +2 … +5 | amber "N min late" |
  | ≥ +6 | red "N min late" |

- **Last bus:** a "LAST BUS" tag when the departure matches
  `sensor.bus_last_departure` (time and line).
- **Trust:** anything untrustworthy is drawn grey. The header shows
  **STALE** (amber) when HA's feed is stale or a departure is more than 2 min
  overdue, and **NO HA** (red) when the API connection is lost.
- **Overnight:** when there's no departure (state `unknown`, or the last one
  is more than 30 min gone), a calm "No more buses tonight" screen, with
  "First bus HH:MM" if that sensor exists.

## Brightness

- **Auto brightness** (switch in HA): follows the **sun's elevation**
  (`sun.sun`), full at ≥ 4° and down to 35% at ≤ −6°. Not the LDR: see the
  [board notes](../../boards/cyd-2432s028.md#quirks-found-on-the-real-hardware).
- **Screen off at night** (switch) with **Screen off at** / **Screen on at**
  (time entities in HA, default 23:00–06:30).
- **Tap anywhere:** full brightness for 30 s, then back to whatever applies.
- With auto off, the Backlight light in HA sets a manual level, and a tap
  returns to it afterwards.

## Home Assistant entities it reads

| Entity | State / attribute | Used for |
|---|---|---|
| `sensor.bus_next_high_street` | state | is there a departure (`unknown`/`unavailable` = none) |
| `sensor.bus_next_high_street` | `line`, `destination`, `scheduled`, `delay`, `live`, `following` | the departure |
| `sensor.bus_oxontime_high_street` | `stale`, `quiet` | STALE warning; suppressed while `quiet` (overnight pause) |
| `sensor.bus_last_departure` | state + `line` | LAST BUS tag |
| `sensor.bus_first_high_street` | state `HH:MM` | "First bus" on the night screen (optional) |
| `sun.sun` | `elevation` | auto brightness |

Things that tripped us up:
- **Booleans arrive as `on`/`off`.** That's how HA's ESPHome integration sends
  bool attributes. The display also accepts `true`/`True`/`1`.
- **HA doesn't clear attributes when a state goes `unknown`.** So "is there a
  bus" is decided by the entity state, never by the attributes.
- **`line` can be a number (`700`) or text (`S9`).** Everything is read as text.

## Settings (substitutions, override in the device file)

| Substitution | Default | Meaning |
|---|---|---|
| `early_warn` / `late_amber` / `late_red` | −2 / 2 / 6 | lateness thresholds (minutes) |
| `overdue_after` / `gone_after` | 2 / 30 | minutes past departure → stale / treated as gone |
| `sun_day_deg` / `sun_night_deg` | 4 / −6 | sun elevation for full / minimum brightness |
| `bl_min` / `bl_max` | 0.35 / 1.0 | brightness range (0–1) |
| `touch_boost_s` | 30s | how long a tap brightens the screen |

The single-stop layout's entity IDs are fixed in the project file (High
Street). The two-stop layout takes them as substitutions (below).

## Two stops (480×320)

```
+-----------------------+-----------------------+
| o NO HA                                 19:42 |  connection + clock
| HIGH STREET           | MARKET SQUARE         |  stop names
|  17         +------+  |   4         +------+  |
|             |  S9  |  |             | 700  |  |  minutes to go, route
|  min        +------+  |  min          STALE   |  feed warning
|  19:59   [ On time ]  |  19:46  [2 min late]  |  expected time, lateness
|  to Wantage           |  to Oxford            |
|  Then 20:29 S9        |  Then 19:58 700       |  following / LAST BUS
+-----------------------+-----------------------+
```

Each card follows the same rules as the single-stop screen. **STALE** shows
under the route badge of the card whose feed is stale; **NO HA** shows once,
in the top bar.

Set each stop in the device file (`s1_` left card, `s2_` right card):

| Substitution | Entity | Provides |
|---|---|---|
| `sN_title` | | card heading (about 13 characters fit) |
| `sN_next` | e.g. `sensor.bus_next_high_street` | state + `line`, `destination`, `scheduled`, `delay`, `live`, `following` |
| `sN_feed` | e.g. `sensor.bus_oxontime_high_street` | `stale`, `quiet` |
| `sN_last` | e.g. `sensor.bus_last_high_street` | state `HH:MM` + `line` |
| `sN_first` | e.g. `sensor.bus_first_high_street` | state `HH:MM` (optional) |

Two stops can share an entity (for example one `sensor.bus_last_departure`)
if that's what HA has.

### Tested

On the 4" board with the demo build
([`esp32-4in-bus-display-demo.yaml`](../../tools/demo/esp32-4in-bus-display-demo.yaml)),
which cycles both cards through every state. **Not yet run with HA**: the
device file's stops are placeholders.

## Open questions for the HA side

1. Create `sensor.bus_first_high_street` (first departure next service day,
   `HH:MM`).
2. Confirm `stale` = the poller hasn't refreshed recently, and `quiet` = the
   deliberate 01:00–04:30 pause.
3. Is `sensor.bus_last_departure` for High Street or all stops? If it isn't
   High Street's, the LAST BUS tag never shows. A per-stop
   `sensor.bus_last_high_street` would fix it.
