"""Log local air traffic over time to find out what the frame should show.

Polls the API on a fixed interval, runs the display pipeline, and writes
one CSV row per round. Raw responses are kept as samples.

Run from the project root:

    python -m tools.traffic_log
    python -m tools.traffic_log --minutes 120 --interval 300

Stop early with Ctrl-C; the summary is printed either way.
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from planeframe import filters
from planeframe.models import aircraft_from_response
from planeframe.sources.airplanes_live import SourceError, fetch_aircraft

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"
LOGS_DIR = ROOT / "data" / "logs"

FIELDNAMES = [
    "timestamp",
    "raw",
    "airline",
    "in_range",
    "shown",
    "top",
    "changed",
]


def run_round(lat: float, lon: float, radius_km: float, limit: int) -> tuple[dict, dict]:
    """Fetch once and measure what survives each stage of the pipeline.

    Returns the raw response and a row describing this round.
    """
    response = fetch_aircraft(lat=lat, lon=lon, radius_km=radius_km)

    planes = aircraft_from_response(response)
    raw = len(planes)

    planes = filters.keep_airline_flights(planes)
    airline = len(planes)

    planes = filters.remove_grounded(planes)
    planes = filters.remove_unusable_position(planes)
    planes = filters.remove_old_position(planes)
    planes = filters.remove_no_distance(planes)
    planes = filters.remove_too_far(planes, radius_km)
    in_range = len(planes)

    planes = filters.sort_by_distance(planes)
    planes = filters.take_nearest(planes, limit)

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "raw": raw,
        "airline": airline,
        "in_range": in_range,
        "shown": len(planes),
        "top": " ".join(plane.callsign for plane in planes),
        "changed": "",
    }
    return response, row


def save_sample(response: dict, stamp: str) -> None:
    """Keep the raw response so it can be replayed later."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    path = SAMPLES_DIR / f"{stamp}.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(response, handle, indent=2)


def summarise(rows: list[dict]) -> None:
    """Print the numbers that decide the display and refresh settings."""
    if not rows:
        print("\nNo rounds completed.")
        return

    counts = [row["in_range"] for row in rows]
    empty = sum(1 for count in counts if count == 0)
    comparable = [row for row in rows if row["changed"] != ""]
    changed = sum(1 for row in comparable if row["changed"] == "yes")

    print(f"\n{len(rows)} rounds")
    print(f"in range: min {min(counts)}, max {max(counts)}, avg {sum(counts) / len(counts):.1f}")
    print(f"empty rounds: {empty} ({empty / len(rows) * 100:.0f}%)")

    if comparable:
        share = changed / len(comparable) * 100
        print(f"top changed: {changed} of {len(comparable)} ({share:.0f}%)")
        print(f"a refresh would be skipped roughly {100 - share:.0f}% of the time")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=60, help="how long to run")
    parser.add_argument("--interval", type=int, default=60, help="seconds between rounds")
    parser.add_argument("--radius", type=float, default=40, help="radius in km")
    parser.add_argument("--limit", type=int, default=3, help="aircraft shown on the frame")
    parser.add_argument("--no-samples", action="store_true", help="do not save responses")
    args = parser.parse_args()

    load_dotenv()
    lat = float(os.environ["HOME_LAT"])
    lon = float(os.environ["HOME_LON"])

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = LOGS_DIR / f"traffic-{started}.csv"

    deadline = time.monotonic() + args.minutes * 60
    rows: list[dict] = []
    previous_top = None
    failures = 0

    print(f"Logging to {log_path.relative_to(ROOT)}")
    print(f"{args.minutes} min at {args.interval} s intervals, {args.radius:.0f} km radius\n")

    with open(log_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()

        try:
            while time.monotonic() < deadline:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

                try:
                    response, row = run_round(lat, lon, args.radius, args.limit)
                except SourceError as exc:
                    failures += 1
                    print(f"{stamp}  fetch failed: {exc}")
                    time.sleep(args.interval)
                    continue

                if previous_top is not None:
                    row["changed"] = "yes" if row["top"] != previous_top else "no"
                previous_top = row["top"]

                if not args.no_samples:
                    save_sample(response, stamp)

                writer.writerow(row)
                handle.flush()
                rows.append(row)

                print(
                    f"{row['timestamp']}  raw {row['raw']:>3}"
                    f"  airline {row['airline']:>2}"
                    f"  in range {row['in_range']:>2}"
                    f"  {row['changed'] or '-':<3}  {row['top']}"
                )

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped early.")

    if failures:
        print(f"\n{failures} rounds failed to fetch.")
    summarise(rows)


if __name__ == "__main__":
    main()