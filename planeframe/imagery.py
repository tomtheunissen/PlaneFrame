"""Find the illustration that belongs to an aircraft.

Two layers, most specific first:

    assets/aircraft/livery/RYR-B738.png   this operator, this type
    assets/aircraft/type/B738.png         any operator, this type

The livery layer is what the frame is really for. The type layer is a
plain white template that catches operators no livery has been drawn for
yet, so a KLM 737 still shows up as a 737 rather than disappearing.
"""

from functools import lru_cache
from pathlib import Path

from planeframe.models import Aircraft

ROOT = Path(__file__).resolve().parents[1]
AIRCRAFT_DIR = ROOT / "assets" / "aircraft"
LIVERY_IMAGES = AIRCRAFT_DIR / "livery"
TYPE_IMAGES = AIRCRAFT_DIR / "type"


def livery_key(plane: Aircraft) -> str | None:
    """The OPERATOR-TYPE key this aircraft would be drawn under.

    Returns None when either half is unknown, which is also the filename
    without its extension: RYR-B738.
    """
    if not plane.airline_code or not plane.type_code:
        return None
    return f"{plane.airline_code}-{plane.type_code}"


@lru_cache(maxsize=1)
def available_liveries() -> frozenset[str]:
    """The OPERATOR-TYPE keys we have drawn.

    Read once. A PNG added while the server is running is only picked up
    after a restart.
    """
    if not LIVERY_IMAGES.is_dir():
        return frozenset()
    return frozenset(path.stem.upper() for path in LIVERY_IMAGES.glob("*.png"))


@lru_cache(maxsize=1)
def available_types() -> frozenset[str]:
    """The type codes we have a plain template for."""
    if not TYPE_IMAGES.is_dir():
        return frozenset()
    return frozenset(path.stem.upper() for path in TYPE_IMAGES.glob("*.png"))


def image_for(plane: Aircraft) -> Path | None:
    """Return the best illustration for this aircraft, or None."""
    key = livery_key(plane)
    if key and key in available_liveries():
        return LIVERY_IMAGES / f"{key}.png"

    if plane.type_code and plane.type_code in available_types():
        return TYPE_IMAGES / f"{plane.type_code}.png"

    return None


def is_drawable(plane: Aircraft) -> bool:
    """Whether either layer can produce an illustration."""
    key = livery_key(plane)
    if key and key in available_liveries():
        return True
    return bool(plane.type_code) and plane.type_code in available_types()


def keep_drawable(aircraft: list[Aircraft]) -> list[Aircraft]:
    """Keep only aircraft we can actually illustrate.

    This doubles as a filter for business jets and unusual military
    types: nothing gets drawn for them, so nothing is worth showing.
    """
    return [plane for plane in aircraft if is_drawable(plane)]


if __name__ == "__main__":
    from planeframe.models import aircraft_from_response
    from planeframe.sources.airplanes_live import load_sample

    print(f"{len(available_liveries())} liveries, {len(available_types())} templates\n")

    result = load_sample("data/samples/20260808-163007.json")
    planes = aircraft_from_response(result)

    for plane in planes:
        path = image_for(plane)
        if path is None:
            source = "-"
        elif path.parent == LIVERY_IMAGES:
            source = f"livery  {path.name}"
        else:
            source = f"type    {path.name}"
        print(f"{plane.callsign or '-':<10} {plane.type_code or '-':<5} {source}")