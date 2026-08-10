"""Find the illustration that belongs to an aircraft."""

from functools import lru_cache
from pathlib import Path

from planeframe.models import Aircraft

ROOT = Path(__file__).resolve().parents[1]
TYPE_IMAGES = ROOT / "assets" / "aircraft" / "type"


@lru_cache(maxsize=1)
def available_types() -> frozenset[str]:
    """The ICAO type codes we have an illustration for.

    Reads the directory once. A PNG added while the server is running is
    only picked up after a restart.
    """
    if not TYPE_IMAGES.is_dir():
        return frozenset()
    return frozenset(path.stem for path in TYPE_IMAGES.glob("*.png"))


def image_for(plane: Aircraft) -> Path | None:
    """Return the path to this aircraft's illustration, if there is one."""
    if not plane.type_code:
        return None

    path_type_image = TYPE_IMAGES / f"{plane.type_code}.png"
    if path_type_image.exists():
        return path_type_image
    return None


def keep_drawable(aircraft: list[Aircraft]) -> list[Aircraft]:
    """Keep only aircraft we can actually illustrate.

    This doubles as a filter for business jets and unusual military
    types: nothing gets drawn for them, so nothing is worth showing.
    """
    types = available_types()
    return [plane for plane in aircraft if plane.type_code in types]


if __name__ == "__main__":
    from planeframe.models import aircraft_from_response
    from planeframe.sources.airplanes_live import load_sample

    print(f"{len(available_types())} illustrations available")
    print(" ".join(sorted(available_types())))
    print()

    result = load_sample("data/samples/20260808-163007.json")
    planes = aircraft_from_response(result)

    for plane in planes:
        path = image_for(plane)
        found = path.name if path else "-"
        print(f"{plane.callsign or '-':<10} {plane.type_code or '-':<5} {found}")