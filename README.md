# PlaneFrame

A framed colour e-ink display showing which aircraft are currently overhead,
drawn as illustrations rather than a list.

A server fetches live flight data, looks up an illustration for each
aircraft, renders a 1600x1200 image, and a battery-powered ESP32 wakes every
ten minutes to pull that image onto a 13.3" E Ink Spectra 6 panel. The frame
hangs on the wall and reads as a print, not as a screen.

## Status

Early development. The data pipeline is taking shape; nothing runs on
hardware yet.

| Component | State |
|---|---|
| `sources/airplanes_live` | done |
| `models` | done |
| `units` | done |
| `filters` | done |
| `imagery`, `palette`, `render` | not started |
| `schedule` | not started |
| `state`, `notify` | not started |
| `web` | not started |
| firmware | not started |

## How it works

The device is deliberately dumb. Every wake it sends its telemetry, receives
a finished framebuffer, and gets its next sleep interval back in the
response headers. All logic lives on the server.

```
airplanes.live -> sources -> models -> filters -> imagery -> render -> web
                                                                        |
                                                             ESP32  <---+
                                                               |
                                                    13.3" Spectra 6 panel
```

This matters more with a colour panel than with monochrome: a full refresh
takes around 30 seconds and dominates the power budget. Keeping the device
asleep and dumb is what makes battery operation viable.

The split also means the layout can change without reflashing, and settings
can be edited from a phone while the device knows nothing about it.

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

Secrets and anything that should not reach version control live in `.env`.
See `.env.example` for the required keys.

| Key | Purpose |
|---|---|
| `HOME_LAT` / `HOME_LON` | observer position, three decimals is plenty |
| `NTFY_TOPIC` | push notifications for low battery and silence |
| `NTFY_SERVER` | ntfy instance to use |
| `DEVICE_TOKEN` | shared secret between server and device |

Runtime settings (radius, intervals, how many aircraft to show) live in
`data/settings.json` and are editable from the dashboard. Refresh schedules
live in `data/routines.json`.

## Usage

Fetch live data and save it as a sample:

```bash
python -m planeframe.sources.airplanes_live
```

Parse a saved sample into aircraft objects:

```bash
python -m planeframe.models
```

Run the full selection pipeline against a sample:

```bash
python -m planeframe.filters
```

Modules are run with `-m` from the project root so package imports resolve
correctly.

## Working with samples

Saved API responses in `data/samples/` are the main development tool.
Working from a sample is instant, needs no network, and returns identical
data every run, so any change in output comes from the code rather than from
a different aircraft happening to fly past.

Worth collecting: a busy afternoon, a quiet night, an aircraft on the
ground, and any response that once caused a bug.

Samples are deliberately kept out of version control. Every response
contains a bearing and distance to the observer for each aircraft, which
together pin down the observer's position quite precisely.

## Data sources

**Flight data:** [airplanes.live](https://airplanes.live). No API key
required, one request per second, non-commercial use only.

**Airline data:** [OpenFlights](https://openflights.org/data.php), used
under the [Open Database License (ODbL)
1.0](https://opendatacommons.org/licenses/odbl/1-0/). The `airlines.dat`
snapshot in `data/` is unmodified. Note that the airline table has not been
maintained in years; it is good enough to recognise an operator code, less
good as a source of current airline names.

The `sources/` package is the only part of the codebase that knows where
flight data comes from. Adding a local RTL-SDR receiver running dump1090
later means adding one module there, with nothing else changing.

## Filtering

Only airline traffic is shown. The strongest signal separating airline
flights from private aircraft is that private callsigns are simply the
registration, while airline callsigns are an ICAO operator code plus a
flight number. Aircraft with a callsign but no registration cannot be
compared that way, so the operator list closes the gap.

Gliders and light aircraft dominate the local airspace on a summer
afternoon and would otherwise fill the frame.

## Illustrations

Each aircraft is drawn as a side-profile illustration on a flat background,
looked up in this order:

1. `assets/aircraft/airline/` — livery for a specific operator and type
2. `assets/aircraft/type/` — neutral profile for the type code
3. `assets/aircraft/fallback/` — silhouette by category

Illustrations are PNGs with a transparent background, all facing the same
direction, and scaled relative to each other so an A380 is visibly larger
than a 737.

Flat colour is a deliberate choice. Spectra 6 uses six primaries with
waveform-level dithering, so photographs are possible but sky gradients
dither into visible noise. Flat shapes with hard edges quantise cleanly.

Note on licensing: aircraft photographs are copyrighted by the photographer
and are not redistributable. Only self-drawn or openly licensed artwork
belongs in this repository.

## Refresh routines

A routine is a time window with its own interval. The server evaluates which
one applies on every wake and returns the result as a sleep duration, so the
device never needs a calendar of its own.

| Routine | When | Interval |
|---|---|---|
| default | always, lowest priority | 10 min |
| night | 23:00 to 07:00 | off |
| away | weekdays 08:30 to 17:00 | 60 min |
| holiday | date range, highest priority | off |

Combined with skipping refreshes when the rendered image has not changed,
this is what turns roughly eight weeks of battery life into roughly twenty.

## Project layout

```
planeframe/
├── planeframe/
│   ├── config.py           settings loading and validation
│   ├── units.py            conversion constants
│   ├── models.py           Aircraft class, parsing
│   ├── filters.py          selecting and sorting
│   ├── imagery.py          illustration lookup
│   ├── palette.py          six-colour palette and quantisation
│   ├── render.py           image composition
│   ├── schedule.py         refresh routines
│   ├── state.py            device telemetry
│   ├── notify.py           battery and silence alerts
│   └── sources/            data sources
├── web/                    FastAPI service, settings and routines forms
├── assets/
│   ├── fonts/
│   └── aircraft/           illustrations
├── data/
│   ├── settings.json
│   ├── routines.json
│   ├── airlines.dat        OpenFlights snapshot
│   └── samples/            saved API responses, not in version control
└── output/                 rendered images
```

## Hardware

Planned, not yet built. No soldering required if ordered in these variants.

| Part | Note |
|---|---|
| 13.3" E Ink Spectra 6, 1600x1200 | designed for signage; full refresh 25-35 s |
| ESP32-S3 e-paper driver board | sold as a kit with the panel |
| LiPo 10000 mAh | charges over USB-C at roughly 500 mA, so expect a long charge |
| Frame with depth, glass removed | e-ink is reflective; glass ruins the paper look |

Rough power budget: about 1.0 mAh per full refresh, dominated by the 30
seconds the panel spends sorting its pigment particles. A skipped refresh
costs about a fifth of that.

These figures are estimates with meaningful uncertainty. The device reports
its own battery voltage on every wake, so the real consumption curve will
replace them within a couple of weeks of running.

## Licence

MIT. See [LICENSE](LICENSE).

The bundled OpenFlights airline data is covered separately by ODbL 1.0, as
described under Data sources.