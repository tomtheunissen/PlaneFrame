from pathlib import Path

from planeframe.models import Aircraft

ROOT = Path(__file__).resolve().parents[1]
TYPE_IMAGES = ROOT / "assets" / "aircraft" / "type"

def image_for(plane: Aircraft) -> Path | None:
    if not plane.type_code:
        return None
    
    path_type_image = TYPE_IMAGES / f"{plane.type_code}.png"
    if path_type_image.exists():
        return path_type_image
    return None

if __name__ == "__main__":
    from planeframe.models import aircraft_from_response
    from planeframe.sources.airplanes_live import load_sample
    from planeframe.filters import select_for_display

    result = load_sample("data/samples/20260808-163007.json")
    planes = aircraft_from_response(result)
    planes = select_for_display(planes)