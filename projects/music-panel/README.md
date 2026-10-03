# Project: music panel (Music Assistant)

[`music-panel.yaml`](music-panel.yaml): choose a speaker or group, choose one
of your **Music Assistant favourites** (radio, playlists, albums), and it
plays there. The bar at the bottom shows what's playing on the chosen
speaker, with previous / play-pause / stop / next and a volume button that
opens a large volume panel.

**Needs from the board:** a 480×320 landscape LVGL display `tft`, a
calibrated touchscreen `touch`, light `backlight`. Used by
[`esp32-4in-music-panel`](../../esp32-4in-music-panel.yaml) (4" ST7796S).

```
+----------------------------------------------+
| [Living ][Living ][ NAD  ][Kitchen][Utility]|  speakers / MA groups
| [Room Sy][ Room  ][      ][       ][ Room  ]|
| [ Radio ]    [ Playlists ]    [ Albums ]     |  which favourites
| +--------------------+ +-------------------+ |
| | BBC Radio 6 Music  | | I Should Coco     | |  your MA favourites,
| |                    | | Supergrass        | |  two columns, scrolls
| +--------------------+ +-------------------+ |
| Song title     |<< >|| [] >>|  [vol 35%]   |  now playing; the volume
| Artist                                       |  button opens a big panel
+----------------------------------------------+
```

## How it works

- **Favourites come from Music Assistant, live.** Opening a tab (and
  connecting to HA) calls `music_assistant.get_library` with
  `favorite: true`. Heart something in MA and it's on the panel the next time
  you open that tab. No reflash.
- **HA trims the answer first.** The call uses ESPHome's `capture_response`
  with a `response_template`, so HA sends only `[name, media id, artists]`
  per item: about 150 bytes for three stations instead of MA's ~730. The
  board has no PSRAM, so this matters as the lists grow. Up to `fav_limit`
  (30) per tab.
- **Tap a favourite:** `music_assistant.play_media` on the chosen speaker,
  `enqueue: replace`.
- **Now playing** reads the chosen speaker's state, `media_title`,
  `media_artist` and `volume_level`. Transport buttons call
  `media_player.media_previous_track` / `media_play_pause` / `media_stop` /
  `media_next_track`.
- **Volume:** the bar's volume button shows the level and opens a panel with
  a long slider (sent when you let go) and big −/+ buttons (5% steps, easier
  on resistive touch). It closes 6 s after the last touch, or with Done. A
  slider squeezed into the bar was too small to use.
- **Screen off** after "Screen timeout" (number in HA, default 60 s); the
  first tap only wakes it, as on the light panel.
- No album art: without PSRAM there's no room for images.

## Home Assistant side: required

- The **Music Assistant** integration, and some **favourites** in MA (the
  heart, on stations from a provider such as BBC Sounds, on playlists and on
  albums). An empty tab says "No favourite … yet".
- In **Settings → Devices & services → ESPHome**, open the panel's entry,
  **Configure**, and tick **"Allow the device to perform Home Assistant
  actions"**. Without it, nothing loads or plays.

## Settings (device file)

| Substitution | Meaning |
|---|---|
| `ma_config_entry` | your MA config entry id: Developer tools → Actions → "Music Assistant: Get library", pick the instance, switch to YAML mode |
| `sp1_name` … `sp5_name` | button labels; they wrap onto two lines (about 11 characters each) |
| `sp1_entity` … `sp5_entity` | any MA `media_player`, including MA groups |
| `fav_limit` | most favourites per tab (default 30) |

There are exactly five speaker buttons. For a different number, change the
`spN` blocks (buttons, sensors) and the lists of five in the scripts.

## Things that tripped us up

- **LVGL labels only cut off with "…" at a fixed height.** Without one, a
  long album name wrapped onto the artist line.
- **A flex layout can't be declared on an empty container** in ESPHome's
  LVGL (and isn't compiled in unless YAML uses it), so the favourite buttons
  are placed in two columns by hand.
- **ESPHome strips `//` comments from lambdas** and doesn't recognise C++ raw
  strings, so the demo's fake media ids avoid `//`. Real ids
  (`library://radio/1`) arrive from HA at runtime and aren't affected.

## Tested

- **Demo** ([`esp32-4in-music-panel-demo.yaml`](../../tools/demo/esp32-4in-music-panel-demo.yaml))
  on the 4" board: speaker selection and now-playing states, three tabs,
  scrolling, each tap logs the right media id. The first build drew a long
  album name over its artist line; the fix (fixed label heights) isn't yet
  rechecked on the board.
- **Live with HA** (2026-10-04): favourites load from MA through
  `capture_response`, tapping one plays it on the chosen speaker, and
  pause/play, stop and the volume panel work. Speaker entities were checked
  against their devices first: an HA name like "Living Room" can belong to
  the TV rather than the speaker you meant.
