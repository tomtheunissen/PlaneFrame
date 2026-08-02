from dataclasses import dataclass
from planeframe.sources.airplanes_live import load_sample

@dataclass
class Aircraft:
    icao: str
    callsign: str | None = None
    registration: str | None = None
    type_code: str | None = None
    description: str | None = None
    altitude_ft: int | None = None
    on_ground: bool = False
    ground_speed_kt: float | None = None
    track: float | None = None
    latitude: float| None = None
    longitude: float | None = None
    category: str | None = None
    position_age_s: float | None = None
    distance_nm: float | None = None
    bearing: float | None = None

    @classmethod
    def from_dict(cls, data: dict):
        """Build an Aircraft from one entry in the API's 'ac' list."""

        callsign = data.get("flight", "").strip() or None

        alt_baro = data.get("alt_baro")
        if isinstance(alt_baro, (int, float)):
            altitude_ft = int(alt_baro)
            on_ground = False
        else:
            altitude_ft = None
            on_ground = alt_baro == "ground"

        return cls(
            icao=data["hex"],
            callsign=callsign,
            registration=data.get("r"),
            type_code=data.get("t"),
            description=data.get("desc"),
            latitude=data.get("lat"),
            longitude=data.get("lon"),
            altitude_ft=altitude_ft,
            on_ground=on_ground,
            ground_speed_kt=data.get("gs"),
            track=data.get("track"),
            category=data.get("category"),
            position_age_s=data.get("seen_pos"),
            distance_nm=data.get("dst"),
            bearing=data.get("dir"),
        )


def aircraft_from_response(data: dict) -> list[Aircraft]:
    """Convert a full API response into a list of Aircraft objects.

    Entries that cannot be parsed are skipped rather than aborting the
    whole batch, so one malformed record does not blank the display.
    """
    aircraft = []
    skipped = 0

    for raw in data.get("ac", []):
        try:
            aircraft.append(Aircraft.from_dict(raw))
        except (KeyError, TypeError, ValueError):
            skipped += 1

    if skipped:
        print(f"Skipped {skipped} unparsable entries")

    return aircraft

if __name__ == "__main__":
    from planeframe.sources.airplanes_live import load_sample

    result = load_sample("data/samples/20260802-192448.json")
    planes = aircraft_from_response(result)

    print(f"{len(planes)} aircraft parsed")
    for plane in planes:
        print(f"{plane.callsign or '-':<10} {plane.type_code or '-':<6} {plane.altitude_ft or '-'}")