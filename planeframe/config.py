from pathlib import Path

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
