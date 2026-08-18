from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

AIRCRAFT_DIR = ROOT / "assets" / "aircraft"
LIVERY_IMAGES = AIRCRAFT_DIR / "livery"
TYPE_IMAGES = AIRCRAFT_DIR / "type"
AIRLINES_PATH = DATA / "airlines.csv"
SAMPLES = DATA / "samples"
LOGS = DATA / "logs"

FONTS = ROOT / "assets" / "fonts"
OUTPUT = ROOT / "output"
REGULAR = FONTS / "Inter_18pt-Regular.ttf"
SEMIBOLD = FONTS / "Inter_18pt-SemiBold.ttf"


BASE_URL = "https://api.airplanes.live/v2/point"
MAX_RADIUS_NM = 250


MISSING_VALUES = {"N/A", r"\N", ""}
ALLOWED_CATEGORIES = {"A2", "A3", "A4", "A5"}


@dataclass
class Settings:
    """All the configureable settings for the end-user"""

    radius_km: int = 40
    limit: int = 3
    max_age_s: int = 30
    require_image: bool = True
    width: int = 1200
    height: int = 1600
    background: tuple[int, int, int] = (186, 226, 245)
    margin: int = 50
    title_size: int = 50
    detail_size: int = 35
    plane_heigt: int = 220
    gap: int = 20
    ink: tuple[int, int, int] = (0, 0, 0)


settings = Settings()