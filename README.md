# Volumio Controller

A physical hardware controller for [Volumio](https://volumio.com/), built around rotary encoders and a 12-character alphanumeric LED display. Designed to run on a Raspberry Pi alongside a Volumio music server, it provides a hands-on physical interface for playback control, volume, seeking, and library browsing — no screen or keyboard required.

## Features

- Real-time playback control via 4 rotary encoders
- 12-character 14-segment LED display showing track info, artist, elapsed time, and clock
- Scrolling marquee for long titles
- Interactive music library browser
- Sleep mode with display dimming
- Safety lock (unlocker mechanism)
- Graceful shutdown support
- Runs as a systemd service on boot

## Hardware

| Component | Details |
|-----------|---------|
| Rotary encoders | 4x Adafruit Seesaw (I2C addresses `0x36`, `0x37`, `0x38`, `0x3a`) |
| LED display | 3x Adafruit HT16K33 14-segment 4-char modules, 12 chars total (I2C addresses `0x70`, `0x71`, `0x72`) |
| Host | Raspberry Pi running Volumio |

## Controls

| Encoder | Rotation | Press |
|---------|----------|-------|
| 1 | Volume up / down | System shutdown |
| 2 | Seek forward / backward | Back / cancel |
| 3 | Toggle sleep mode | Open music library menu |
| 4 | Next / previous track | Play / Pause / Stop |

## Architecture

The application is **multi-threaded and event-driven**, built around a hierarchical state machine.

```
__main__.py
└── main_thread.py
    ├── volumio_thread.py       — Socket.IO connection to Volumio (localhost:3000)
    ├── radio_state_machine.py  — Core state machine (playing, paused, sleeping, menu...)
    ├── user_input_listener.py  — Hardware input polling (4x rotary encoders)
    ├── display_state.py        — Display coordinator (brightness, text, threads)
    │   ├── PersistentDisplayThread         — Looping scrolling text
    │   ├── TemporaryDisplayThread          — Timed messages
    │   ├── PlayingTrackDisplayThread       — Current track & artist
    │   ├── PlayingTrackElapsedTimeThread   — Playback progress
    │   ├── DatetimeDisplayThread           — Date & time
    │   └── ActiveToQuietDisplayThread      — Brightness transition
    ├── menu_thread.py          — Interactive library browser UI
    ├── volumio_menu.py         — REST API browsing with URI caching
    ├── vigie_thread.py         — Monitors Volumio state changes
    └── unlocker.py             — Safety lock
```

### State Machine States

- `connecting` — waiting for Volumio connection
- `home_playing` — music is playing
- `home_holding` — music is paused
- `home_sleeping` — stopped / idle
- `menu` — browsing music library
- `shutting_down` — graceful shutdown in progress

## Installation

### Software Prerequisites

- Volumio OS 4 for Raspberry Pi

### Hardware Prerequisites

- 1 x Raspberry Pi compatible with Volumio OS 4
- 3 x Adafruit 14-segment LED Alphanumeric Backpack - STEMMA QT
- 3 x Dual Alphanumeric Display - White 0.54" Digit Height - Pack of 2
- 4 x Adafruit I2C Stemma QT Rotary Encoder Breakout
- 4 x Rotary Encoders compatible with Stemma QT Rotary Encoder

### Automated install

Run the install script from the Volumio device:

```bash
bash install.sh
```

This will clone the repository, install Python dependencies, set up the systemd service, and start it automatically.

### Manual install

```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install -r requirements.txt
```

Then run:

```bash
python3 .
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `Adafruit-Blinka` | 8.69.0 | GPIO / I2C abstraction layer |
| `adafruit-circuitpython-ht16k33` | 4.6.15 | 14-segment LED display driver |
| `adafruit-circuitpython-seesaw` | 1.16.8 | Rotary encoder driver |
| `python-socketio` | 4.6.1 | Real-time communication with Volumio |
| `transitions` | 0.9.3 | Hierarchical state machine |
| `Unidecode` | 1.4.0 | Accent/diacritic removal for display |
| `requests` | 2.32.5 | Volumio REST API calls |
| `pytz` | 2025.2 | Timezone support for clock display |