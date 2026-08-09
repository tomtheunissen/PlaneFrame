"""Log local air traffic over time to find out what the frame should show.

Polls the API on a fixed interval, runs the display pipeline, and writes
one CSV row per round. Raw responses are kept as samples.

The CSV columns follow filters.pipeline(), so adding or removing a filter
changes the log automatically and the measurement can never drift out of
step with the code it is measuring.

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

from planeframe.filters import pipeline
from planeframe.models import aircraft_from_response
from planeframe.sources.airplanes_live import SourceError, fetch_aircraft

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"
LOGS_DIR = ROOT / "data" / "logs"


def _column(label: str) -> str:
    """Turn a pipeline label into a CSV column name."""
    return label.replace(" ", "_")


def fieldnames(steps: list) -> list[str]:
    """Build the CSV header from the pipeline plus the fixed columns."""
    return ["timestamp", "raw", *[_column(label) for label, _ in steps], "top", "changed"]


def run_round(
    lat: float,
    lon: float,
    radius_km: float,
    limit: int,
    max_age_s: float,
) -> tuple[dict, dict]:
    """Fetch once and measure what survives each stage of the pipeline.

    Returns the raw response and a row describing this round.
    """
    response = fetch_aircraft(lat=lat, lon=lon, radius_km=radius_km)
    planes = aircraft_from_response(response)

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "raw": len(planes),
        "changed": "",
    }

    for label, step in pipeline(radius_km, max_age_s, limit):
        planes = step(planes)
        row[_column(label)] = len(planes)

    row["top"] = " ".join(plane.callsign for plane in planes)
    return response, row


def save_sample(response: dict, stamp: str) -> None:
    """Keep the raw response so it can be replayed later."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    path = SAMPLES_DIR / f"{stamp}.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(response, handle, indent=2)


def summarise(rows: list[dict], final_column: str) -> None:
    """Print the numbers that decide the display and refresh settings."""
    if not rows:
        print("\nNo rounds completed.")
        return

    counts = [row[final_column] for row in rows]
    empty = sum(1 for count in counts if count == 0)
    short = sum(1 for count in counts if 0 < count < max(counts))
    comparable = [row for row in rows if row["changed"] != ""]
    changed = sum(1 for row in comparable if row["changed"] == "yes")

    print(f"\n{len(rows)} rounds")
    print(f"shown: min {min(counts)}, max {max(counts)}, avg {sum(counts) / len(counts):.1f}")
    print(f"empty rounds: {empty} ({empty / len(rows) * 100:.0f}%)")
    print(f"partly filled rounds: {short} ({short / len(rows) * 100:.0f}%)")

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
    parser.add_argument("--max-age", type=float, default=30, help="max position age in seconds")
    parser.add_argument("--no-samples", action="store_true", help="do not save responses")
    args = parser.parse_args()

    load_dotenv()
    lat = float(os.environ["HOME_LAT"])
    lon = float(os.environ["HOME_LON"])

    steps = pipeline(args.radius, args.max_age, args.limit)
    columns = fieldnames(steps)
    final_column = columns[-3]

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
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()

        try:
            while time.monotonic() < deadline:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

                try:
                    response, row = run_round(
                        lat, lon, args.radius, args.limit, args.max_age
                    )
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
                    f"  shown {row[final_column]:>2}"
                    f"  {row['changed'] or '-':<3}  {row['top']}"
                )

                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped early.")

    if failures:
        print(f"\n{failures} rounds failed to fetch.")
    summarise(rows, final_column)


if __name__ == "__main__":
    main()