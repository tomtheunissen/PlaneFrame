"""Select and order the aircraft that should end up on the display."""

from planeframe.models import Aircraft


def remove_grounded(aircraft: list[Aircraft]) -> list[Aircraft]:
    """Drop aircraft that are on the ground."""
    return [plane for plane in aircraft if not plane.on_ground]


def remove_unusable_position(aircraft: list[Aircraft]) -> list[Aircraft]:
    """Drop aircraft with missing latitude or longitude values."""
    return [
        plane
        for plane in aircraft
        if plane.latitude is not None and plane.longitude is not None
    ]


def remove_old_position(aircraft: list[Aircraft], max_age_s: float = 30) -> list[Aircraft]:
    """Drop aircraft whose position is too old to be trusted."""
    return [
        plane
        for plane in aircraft
        if plane.position_age_s is None or plane.position_age_s < max_age_s
    ]


def remove_no_distance(aircraft: list[Aircraft]) -> list[Aircraft]:
    """Drop aircraft with no known distance.

    Running this before sorting means nothing downstream has to guard
    against a missing value.
    """
    return [plane for plane in aircraft if plane.distance_km is not None]


def remove_too_far(aircraft: list[Aircraft], max_distance_km: float = 40) -> list[Aircraft]:
    """Drop aircraft beyond the configured radius."""
    return [plane for plane in aircraft if plane.distance_km <= max_distance_km]


def sort_by_distance(aircraft: list[Aircraft]) -> list[Aircraft]:
    """Order aircraft from nearest to furthest."""
    return sorted(aircraft, key=lambda plane: plane.distance_km)


def take_nearest(aircraft: list[Aircraft], limit: int = 3) -> list[Aircraft]:
    """Keep only the first few aircraft."""
    return aircraft[:limit]


def select_for_display(
    aircraft: list[Aircraft],
    max_distance_km: float = 40,
    max_age_s: float = 30,
    limit: int = 3,
) -> list[Aircraft]:
    """Run the full pipeline from raw aircraft to what the frame shows.

    Filtering happens before sorting so the sort works on the smallest
    possible list.
    """
    aircraft = remove_grounded(aircraft)
    aircraft = remove_unusable_position(aircraft)
    aircraft = remove_old_position(aircraft, max_age_s)
    aircraft = remove_no_distance(aircraft)
    aircraft = remove_too_far(aircraft, max_distance_km)
    aircraft = sort_by_distance(aircraft)
    return take_nearest(aircraft, limit)


if __name__ == "__main__":
    from planeframe.models import aircraft_from_response
    from planeframe.sources.airplanes_live import load_sample

    result = load_sample("data/samples/20260802-192448.json")
    planes = aircraft_from_response(result)
    print(f"{len(planes):>3} before filtering")

    steps = [
        ("grounded", remove_grounded),
        ("no position", remove_unusable_position),
        ("stale position", remove_old_position),
        ("no distance", remove_no_distance),
        ("too far", remove_too_far),
        ("sorted", sort_by_distance),
        ("limited", take_nearest),
    ]

    for label, step in steps:
        planes = step(planes)
        print(f"{len(planes):>3} after {label}")

    print()
    for plane in planes:
        print(f"{plane.callsign:<10} {plane.distance_km:.1f} km")