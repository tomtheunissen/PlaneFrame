# PlaneFrame

An e-ink picture frame that shows which aircraft are currently overhead.

A server fetches live flight data, renders it into an image, and a
battery-powered ESP32 wakes up every few minutes to pull that image and
display it on a 7.5" e-paper panel. The frame hangs on the wall and looks
like a print, not like a screen.

## Status

Early development. The data pipeline is taking shape; nothing is running
on hardware yet.

| Component | State |
|---|---|
| `sources/airplanes_live` | working |
| `models` | working |
| `filters` | not started |
| `render` | not started |
| `state`, `notify` | not started |
| `web` | not started |
| firmware | not started |

## How it works

The device is deliberately dumb. Every wake it sends its telemetry,
receives a finished image, and gets its settings back in the response
headers. All logic lives on the server.

```
airplanes.live  ->  sources  ->  models  ->  filters  ->  render  ->  web
                                                                      |
                                                          ESP32  <----+
                                                            |
                                                       e-paper panel
```

This split means the layout can be changed without reflashing the device,
and it keeps the ESP32 awake for as little time as possible, which is what
determines battery life.

## Setup

```bash
git clone <repo-url>
cd planeframe

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in your coordinates and ntfy topic
```

## Configuration

Secrets and anything that should not end up in version control live in
`.env`. See `.env.example` for the required keys.

| Key | Purpose |
|---|---|
| `HOME_LAT` / `HOME_LON` | observer position, 3 decimals is plenty |
| `NTFY_TOPIC` | push notifications for low battery and silence |
| `NTFY_SERVER` | ntfy instance to use |
| `DEVICE_TOKEN` | shared secret between server and device |

## Usage

Fetch live data and save it as a sample:

```bash
python -m planeframe.sources.airplanes_live
```

Parse a saved sample into aircraft objects:

```bash
python -m planeframe.models
```

Modules are run with `-m` from the project root so that package imports
resolve correctly.

## Working with samples

Saved API responses in `data/samples/` are the main development tool.
Working from a sample is instant, needs no network, and returns identical
data every run, so any change in output comes from the code rather than
from a different aircraft happening to fly past.

Worth collecting: a busy afternoon, a quiet night, an aircraft on the
ground, and any response that once caused a bug.

## Data source

[airplanes.live](https://airplanes.live) — no API key required, one
request per second, non-commercial use.

The `sources/` package is the only part of the codebase that knows where
data comes from. Swapping in a local RTL-SDR receiver running dump1090
later means adding one module there, with nothing else changing.

## Project layout

```
planeframe/
├── planeframe/
│   ├── config.py           settings loading and validation
│   ├── models.py           Aircraft class, parsing
│   ├── filters.py          selecting and sorting
│   ├── render.py           image generation
│   ├── state.py            device telemetry
│   ├── notify.py           battery and silence alerts
│   ├── units.py            conversion constants
│   └── sources/            data sources
├── web/                    FastAPI service and settings form
├── data/
│   ├── settings.json       runtime settings
│   └── samples/            saved API responses
├── output/                 rendered images
└── assets/fonts/           fonts used by the renderer
```

## Hardware

Planned, not yet built.

| Part | Note |
|---|---|
| Waveshare 7.5" e-paper, 800x480 | monochrome; colour panels refresh far slower |
| FireBeetle 2 ESP32-E (with header) | JST battery connector and onboard voltage divider |
| LiPo 3000 mAh | charges over the board's own USB-C |
| A4 frame, glass removed | e-ink is reflective; glass ruins the paper look |

No soldering required if the parts are ordered in these variants.

## Licence

Not decided yet.