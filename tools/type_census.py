"""Count which aircraft types actually appear, to prioritise illustrations.

Walks every saved sample, runs the display pipeline without the image
requirement, and counts how often each ICAO type code survives. The
result is the order in which illustrations are worth collecting.

Filenames in assets/aircraft/type/ must match the code in the first
column exactly, so B738.png, A20N.png, and so on.

Run from the project root:

    python -m tools.type_census
    python -m tools.type_census --top 40
"""

import argparse
from collections import Counter
from pathlib import Path

from planeframe.filters import pipeline
from planeframe.imagery import available_types
from planeframe.models import aircraft_from_response
from planeframe.sources.airplanes_live import SourceError, load_sample

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"


def census(radius_km: float) -> tuple[Counter, dict[str, str]]:
    """Count type codes across all samples, and remember one description each."""
    counts: Counter = Counter()
    names: dict[str, str] = {}
    files = sorted(SAMPLES_DIR.glob("*.json"))

    for path in files:
        try:
            response = load_sample(str(path))
        except SourceError:
            continue

        planes = aircraft_from_response(response)
        # limit high enough that nothing is cut off, image check disabled
        for _label, step in pipeline(
            max_distance_km=radius_km, limit=10_000, require_image=False
        ):
            planes = step(planes)

        for plane in planes:
            counts[plane.type_code] += 1
            if plane.type_code not in names and plane.description:
                names[plane.type_code] = plane.description

    print(f"Read {len(files)} samples")
    return counts, names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=30, help="how many types to list")
    parser.add_argument("--radius", type=float, default=40, help="radius in km")
    args = parser.parse_args()

    counts, names = census(args.radius)
    if not counts:
        print("No samples found.")
        return

    have = available_types()
    total = sum(counts.values())
    running = 0

    print(f"\n{total} sightings, {len(counts)} distinct types\n")
    print(f"{'#':>4} {'CODE':<6} {'SHARE':>6} {'CUMUL':>6}  {'HAVE':<5} DESCRIPTION")
    print("-" * 72)

    for rank, (code, count) in enumerate(counts.most_common(args.top), start=1):
        running += count
        share = count / total * 100
        cumulative = running / total * 100
        mark = "yes" if code in have else "-"
        print(
            f"{rank:>4} {code:<6} {share:>5.1f}% {cumulative:>5.1f}%  "
            f"{mark:<5} {names.get(code, '')}"
        )

    missing = [code for code, _ in counts.most_common(args.top) if code not in have]
    if missing:
        print(f"\nStill needed, in priority order:\n{' '.join(missing)}")
        print("\nSave them as:")
        print(" ".join(f"{code}.png" for code in missing[:10]))


if __name__ == "__main__":
    main()