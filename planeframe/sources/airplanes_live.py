"""Fetch raw aircraft data from api.airplanes.live, or from a saved sample."""

from planeframe.units import KM_PER_NM
import json

import requests

BASE_URL = "https://api.airplanes.live/v2/point"
MAX_RADIUS_NM = 250


class SourceError(Exception):
    """The source could not deliver usable data."""


def _validate(data: dict) -> dict:
    """Check that the response has the shape the rest of the code expects."""
    if not isinstance(data, dict):
        raise SourceError("Response is not an object")
    if "ac" not in data:
        raise SourceError("Response contains no aircraft")
    return data


def fetch_aircraft(lat: float, lon: float, radius_km: float, timeout: float = 10.0) -> dict:
    """Request all aircraft within radius_km of (lat, lon).

    Returns the parsed JSON exactly as the API sends it.
    Raises SourceError if nothing usable comes back.
    """
    radius_nm = radius_km / KM_PER_NM

    if radius_nm <= 0 or radius_nm > MAX_RADIUS_NM:
        raise ValueError(f"Radius out of range: {radius_km} km")

    url = f"{BASE_URL}/{lat}/{lon}/{radius_nm:.1f}"

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.Timeout as exc:
        raise SourceError("No response within the time limit") from exc
    except requests.ConnectionError as exc:
        raise SourceError("Could not connect to the API") from exc
    except requests.HTTPError as exc:
        raise SourceError(f"API returned status {response.status_code}") from exc
    except ValueError as exc:
        raise SourceError("Response was not valid JSON") from exc

    return _validate(data)


def load_sample(path: str) -> dict:
    """Read a previously saved response from a file.

    Returns the same shape as fetch_aircraft, so the rest of the code
    cannot tell the difference.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SourceError(f"Sample does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SourceError(f"Sample contains invalid JSON: {path}") from exc
    except OSError as exc:
        raise SourceError(f"Could not read sample: {path}") from exc

    return _validate(data)


if __name__ == "__main__":
    import os
    from datetime import datetime

    from dotenv import load_dotenv

    load_dotenv()

    # Set to None to hit the live API, or provide a path to work with
    # saved data instead.
    USE_SAMPLE = None

    try:
        if USE_SAMPLE:
            result = load_sample(USE_SAMPLE)
            print(f"Loaded sample: {USE_SAMPLE}")
        else:
            result = fetch_aircraft(
                lat=float(os.environ["HOME_LAT"]),
                lon=float(os.environ["HOME_LON"]),
                radius_km=46,
            )
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            sample_path = f"data/samples/{stamp}.json"
            with open(sample_path, "w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2)
            print(f"Saved sample: {sample_path}")
    except SourceError as exc:
        raise SystemExit(f"Fetch failed: {exc}")

    print(f"{result['total']} aircraft found")
    print(json.dumps(result, indent=2)[:500])