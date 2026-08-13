# PlaneFrame

A framed colour e-ink display showing which aircraft are currently
overhead, drawn as illustrations in their airline's livery.

A server fetches live flight data, looks up an illustration for each
aircraft, renders a 1200x1600 image, and a battery-powered ESP32 wakes
every ten minutes to pull that image onto a 13.3" E Ink Spectra 6 panel
mounted in portrait. The frame hangs on the wall and reads as a print,
not as a screen.

## Status

Early development. The data pipeline is complete; nothing runs on
hardware yet.

| Component | State |
|---|---|
| `sources/airplanes_live` | done |
| `models` | done |
| `units` | done |
| `filters` | done |
| `imagery` | done |
| `render` | in progress |
| `palette` | not started |
| `config` | not started |
| `schedule` | not started |
| `state`, `notify` | not started |
| `web` | not started |
| firmware | not started |

## How it works

The device is deliberately dumb. Every wake it sends its telemetry,
receives a finished framebuffer, and gets its next sleep interval back in
the response headers. All logic lives on the server.

```
airplanes.live -> sources -> models -> filters -> imagery -> render -> web
                                                                        |
                                                             ESP32  <---+
                                                               |
                                                    13.3" Spectra 6 panel
```

This matters more with a colour panel than with monochrome: a full
refresh takes around 30 seconds and dominates the power budget. Keeping
the device asleep and dumb is what makes battery operation viable.

The split also means the layout can change without reflashing, and
settings can be edited from a phone while the device knows nothing about
it.

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

Secrets and anything that should not reach version control live in
`.env`. See `.env.example` for the required keys.

| Key | Purpose |
|---|---|
| `HOME_LAT` / `HOME_LON` | observer position, three decimals is plenty |
| `NTFY_TOPIC` | push notifications for low battery and silence |
| `NTFY_SERVER` | ntfy instance to use |
| `DEVICE_TOKEN` | shared secret between server and device |

Runtime settings (radius, intervals, how many aircraft to show) live in
`data/settings.json` and are editable from the dashboard. Refresh
schedules live in `data/routines.json`.

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

See which illustration each aircraft resolves to:

```bash
python -m planeframe.imagery
```

Measure local traffic over time:

```bash
python -m tools.traffic_log --minutes 180 --interval 600
```

Rank operator and type combinations by how often they appear:

```bash
python -m tools.census --top 60 --types
```

Convert downloaded or generated drawings into usable illustrations:

```bash
python -m tools.prepare_images assets/aircraft/raw
```

Modules are run with `-m` from the project root so package imports
resolve correctly.

## Working with samples

Saved API responses in `data/samples/` are the main development tool.
Working from a sample is instant, needs no network, and returns identical
data every run, so any change in output comes from the code rather than
from a different aircraft happening to fly past.

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
1.0](https://opendatacommons.org/licenses/odbl/1-0/). The snapshot in
`data/airlines.csv` is unmodified. Note that the airline table has not
been maintained in years; it is good enough to recognise an operator
code, less good as a source of current airline names.

**Typeface:** [Inter](https://rsms.me/inter) by Rasmus Andersson,
licensed under the [SIL Open Font License
1.1](https://openfontlicense.org). The licence text is included alongside
the font files in `assets/fonts/`.

The `sources/` package is the only part of the codebase that knows where
flight data comes from. Adding a local RTL-SDR receiver running dump1090
later means adding one module there, with nothing else changing.

## Filtering

Only large airline traffic is shown, decided by three independent
signals.

**Callsign against registration.** Private aircraft transmit their
registration as the callsign, so a match between the two is strong
evidence this is not an airline flight. Where no registration is
reported, an operator code list decides instead.

**Emitter category.** The ADS-B category field reports a mass class.
Anything outside A2 to A5 is dropped, which excludes light aircraft,
gliders and helicopters. A missing category is also dropped: in practice
every airliner reports one, while aircraft found through multilateration
generally do not.

**Whether it can be drawn.** An aircraft with no illustration is not
worth showing, and this catches business jets and unusual military types
without maintaining a list of them. A NATO E-3A that circled overhead for
an hour disappeared the moment this filter was added.

The second signal exists because the first can be defeated by bad data.
One observed ultralight transmitted a callsign that did not match its own
registration, presumably mistyped, and passed the first test. Its
category was A1, so the second test caught it.

## Illustrations

Two layers, most specific first:

```
assets/aircraft/livery/RYR-B738.png   this operator, this type
assets/aircraft/type/B738.png         any operator, this type
```

The key is the ICAO operator code and the ICAO type code joined by a
hyphen, which is also the filename. The livery layer is the point of the
project; the type layer is a plain white template that catches operators
no livery has been drawn for yet, so a KLM 737 still shows up as a 737
rather than disappearing.

`tools/census.py` ranks both layers by how often each key actually
appears overhead, and reports how many illustrations each coverage level
costs. Drawing in that order means the first handful of illustrations
carry most of the traffic.

Illustrations are PNGs with a transparent background, all facing right,
and scaled relative to each other so an A380 is visibly larger than a
737.

Flat colour is a deliberate choice. Spectra 6 uses six primaries with
waveform-level dithering, so photographs are possible but sky gradients
dither into visible noise. Flat shapes with hard edges and no outlines
quantise cleanly.

`docs/illustration-prompt.md` holds the prompt used to generate them, and
`tools/prepare_images.py` handles the background removal, cropping and
mirroring afterwards. Generated images are asked for on flat magenta
rather than transparent: models rarely honour a transparency request, and
white cannot be flood filled away from a white fuselage.

Note on licensing: airline liveries are trademarks and the reference
photos are copyrighted. `assets/aircraft/` stays out of version control.

## Refresh routines

A routine is a time window with its own interval. The server evaluates
which one applies on every wake and returns the result as a sleep
duration, so the device never needs a calendar of its own.

| Routine | When | Interval |
|---|---|---|
| default | always, lowest priority | 10 min |
| night | 23:00 to 07:00 | off |
| away | weekdays 08:30 to 17:00 | 60 min |
| holiday | date range, highest priority | off |

Refreshes are also skipped when the rendered image has not changed. That
saving turned out to be smaller than expected: measured over several
hours at five-minute intervals, the displayed aircraft changed in every
single round. The saving is real at night and during quiet hours, and
close to zero during the day.

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
├── tools/                  measurement and asset scripts
├── docs/                   notes that are not code
├── assets/
│   ├── fonts/              Inter, with its OFL licence text
│   └── aircraft/           illustrations, not in version control
│       ├── livery/         OPERATOR-TYPE.png
│       ├── type/           TYPE.png
│       └── raw/            downloads awaiting conversion
├── data/
│   ├── settings.json
│   ├── routines.json
│   ├── airlines.csv        OpenFlights snapshot
│   ├── logs/               traffic measurements, not in version control
│   └── samples/            saved API responses, not in version control
└── output/                 rendered images
```

## Hardware

Planned, not yet built. No soldering required if ordered in these
variants.

| Part | Note |
|---|---|
| 13.3" E Ink Spectra 6, 1600x1200 | mounted in portrait; full refresh 25-35 s |
| ESP32-S3 e-paper driver board | sold as a kit with the panel |
| LiPo 10000 mAh | charges over USB-C at roughly 500 mA, so expect a long charge |
| Frame with depth, glass removed | e-ink is reflective; glass ruins the paper look |

Rough power budget: about 1.0 mAh per full refresh, dominated by the 30
seconds the panel spends sorting its pigment particles. A skipped refresh
costs about a fifth of that. At ten-minute intervals with a night pause
and a weekday away window, that works out to somewhere around three
months per charge.

These figures are estimates with meaningful uncertainty. The device
reports its own battery voltage on every wake, so the real consumption
curve will replace them within a couple of weeks of running.

## Licence

MIT. See [LICENSE](LICENSE).

The bundled OpenFlights data and the Inter typeface are covered by their
own licences, as described under Data sources.