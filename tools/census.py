"""Count which operator and type combinations actually appear.

Walks every saved sample, runs the display pipeline without the image
requirement, and counts how often each OPERATOR-TYPE pair survives. The
result is the order in which liveries are worth drawing.

The first table is the livery layer: one illustration per pair, named
exactly as the key in the first column, so RYR-B738.png. The second table
is the type layer: plain white templates that catch every operator no
livery exists for yet.

Run from the project root:

    python -m tools.census
    python -m tools.census --top 60
    python -m tools.census --types
"""

import argparse
from collections import Counter
from pathlib import Path

from planeframe.filters import airline_name, pipeline
from planeframe.imagery import available_liveries, available_types, livery_key
from planeframe.models import aircraft_from_response
from planeframe.sources.airplanes_live import SourceError, load_sample

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "data" / "samples"
MILESTONES = (50, 75, 90, 95)


def census(radius_km: float) -> tuple[Counter, Counter, dict[str, str], dict[str, str]]:
    """Count liveries and types across every sample.

    Also remembers one airline name and one description per key, so the
    output is readable without looking anything up.
    """
    liveries: Counter = Counter()
    types: Counter = Counter()
    operators: dict[str, str] = {}
    descriptions: dict[str, str] = {}
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
            types[plane.type_code] += 1
            if plane.type_code not in descriptions and plane.description:
                descriptions[plane.type_code] = plane.description

            key = livery_key(plane)
            if key is None:
                continue
            liveries[key] += 1
            if key not in operators:
                operators[key] = airline_name(plane) or plane.airline_code

    print(f"Read {len(files)} samples")
    return liveries, types, operators, descriptions


def report(
    title: str,
    counts: Counter,
    have: frozenset[str],
    labels: dict[str, str],
    top: int,
) -> list[str]:
    """Print a ranked table and return the keys still missing."""
    total = sum(counts.values())
    running = 0

    print(f"\n{title}")
    print(f"{total} sightings, {len(counts)} distinct\n")
    print(f"{'#':>4}  {'KEY':<10} {'SHARE':>6} {'CUMUL':>6}  {'HAVE':<5} NAME")
    print("-" * 74)

    for rank, (key, count) in enumerate(counts.most_common(top), start=1):
        running += count
        share = count / total * 100
        cumulative = running / total * 100
        mark = "yes" if key in have else "-"
        print(
            f"{rank:>4}  {key:<10} {share:>5.1f}% {cumulative:>5.1f}%  "
            f"{mark:<5} {labels.get(key, '')}"
        )

    return [key for key, _ in counts.most_common(top) if key not in have]


def milestones(counts: Counter) -> None:
    """Show how many illustrations each coverage level costs."""
    total = sum(counts.values())
    running = 0
    reached = {}

    for rank, (_key, count) in enumerate(counts.most_common(), start=1):
        running += count
        share = running / total * 100
        for target in MILESTONES:
            if target not in reached and share >= target:
                reached[target] = rank

    parts = [f"{target}% at {reached[target]}" for target in MILESTONES if target in reached]
    print("\nIllustrations needed: " + ", ".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=40, help="how many rows to list")
    parser.add_argument("--radius", type=float, default=40, help="radius in km")
    parser.add_argument("--types", action="store_true", help="also list the type layer")
    args = parser.parse_args()

    liveries, types, operators, descriptions = census(args.radius)
    if not liveries:
        print("No samples found.")
        return

    missing = report("LIVERY LAYER", liveries, available_liveries(), operators, args.top)
    milestones(liveries)

    if missing:
        print(f"\nStill needed, in priority order:\n{' '.join(missing)}")
        print("\nSave the first few as:")
        print(" ".join(f"{key}.png" for key in missing[:8]))

    if args.types:
        missing_types = report(
            "TYPE LAYER", types, available_types(), descriptions, args.top
        )
        if missing_types:
            print(f"\nStill needed as fallback:\n{' '.join(missing_types)}")


if __name__ == "__main__":
    main()