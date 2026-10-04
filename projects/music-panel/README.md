# Project: music panel (Music Assistant)

[`music-panel.yaml`](music-panel.yaml): choose a speaker or group, choose one
of your **Music Assistant favourites** (radio, playlists, albums), and it
plays there. The bar at the bottom shows what's playing on the chosen
speaker, with previous / play-pause / stop / next, an **announce** button
(hold it: e.g. "Dinner's ready!" in every room) and a volume button that
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
| Song title   |<< >|| [] >>| [plate] [vol] |  now playing; hold the
| Artist                                       |  plate to announce
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
  `media_player.media_previous_track` / `media_play_pause` /
  `media_next_track`.
- **Stop** switches **groups** off (`media_player.turn_off`) and just stops
  **single speakers** (`media_stop`). A Music Assistant group that is only
  stopped stays switched on, and MA then plays anything sent to one of its
  members on the whole group. Single cast speakers can't be switched off, so
  the panel checks each player's `supported_features` (TURN_OFF) to decide.
- **Volume:** the bar's volume button shows the level and opens a panel with
  a long slider (sent when you let go) and big −/+ buttons (5% steps, easier
  on resistive touch). It closes 6 s after the last touch, or with Done. A
  slider squeezed into the bar was too small to use.
- **Announce:** hold the plate button (a short tap just shows "Hold to
  announce"). It runs the HA script in `announce_script`, lights up while
  it's sent, and ignores repeat presses for 10 s. The script decides what's
  said and where; see "Announcement script" below.
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

## Announcement script (HA side)

An example `script.announce_dinner` (Settings → Automations & scenes →
Scripts, YAML mode). Put the sound in `config/www/` (HA serves it at
`/local/...`); a TTS clip made once works well.

```yaml
alias: Announce dinner
icon: mdi:silverware-fork-knife
mode: single
sequence:
  - action: music_assistant.play_announcement
    target:
      entity_id:          # every speaker, one by one (see below)
        - media_player.kitchen
        - media_player.living_room
        - media_player.office
    data:
      url: https://<your HA address>/local/dinner_ready.mp3
      use_pre_announce: true    # MA's chime first
      announce_volume: 60
```

**List the speakers one by one, not a Google speaker group.** Announced to
a Google group (through its MA player) every room heard it in sync, but a
speaker that had been playing on its own did **not** resume afterwards.
Announced to the speakers individually, each one resumed what it was playing
(about 6 s later); they're just not perfectly in sync. Keep a second script
with a test message for trying changes, so nobody thinks dinner's ready.

## Settings (device file)

| Substitution | Meaning |
|---|---|
| `ma_config_entry` | your MA config entry id: Developer tools → Actions → "Music Assistant: Get library", pick the instance, switch to YAML mode |
| `sp1_name` … `sp5_name` | button labels; they wrap onto two lines (about 11 characters each) |
| `sp1_entity` … `sp5_entity` | any MA `media_player`, including MA groups |
| `fav_limit` | most favourites per tab (default 30) |
| `announce_script` | script the plate button runs (default `script.announce_dinner`) |

There are exactly five speaker buttons. For a different number, change the
`spN` blocks (buttons, sensors) and the lists of five in the scripts.

## Things that tripped us up

- **A group that's only stopped captures its members.** With the Downstairs
  group stopped (not off), playing on the Utility Room speaker (a member)
  played on the whole group again. Hence stop = off for groups.
- **MA *sync groups* of Google cast speakers played on one speaker only.** A
  native Google speaker group (made in the Google Home app, then used through
  its Music Assistant player) plays on all of them.
- **Albums failed on Google speakers** while radio worked: HA logged "Failed
  to cast media http://<MA host>:8097/…flac … make sure the URL is reachable
  from the cast device". The panel's request was correct (MA queued the
  album); the stream from MA to the speaker failed. Not solved yet; worth
  trying: MP3 as the speaker's output codec in MA, and checking the speakers
  can reach MA's stream server.
- **Check what an entity really is.** "Living Room" was the Apple TV; the
  Google speaker was "Living Room speaker". Look at the device's model before
  wiring a button.

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
  pause/play, stop (single speakers and a Google group), the volume panel
  and the hold-to-announce button (9 speakers, music resumed) work. Album playback on Google speakers fails on the MA side (see above).
  Speaker entities were checked
  against their devices first: an HA name like "Living Room" can belong to
  the TV rather than the speaker you meant.
