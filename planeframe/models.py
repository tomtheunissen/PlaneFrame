"""Turn raw source data into Aircraft objects."""

from dataclasses import dataclass

from planeframe.units import KM_PER_NM, M_PER_FT


@dataclass
class Aircraft:
    """A single aircraft as reported by a data source."""

    icao: str
    callsign: str | None = None
    registration: str | None = None
    type_code: str | None = None
    description: str | None = None
    altitude_ft: int | None = None
    on_ground: bool = False
    ground_speed_kt: float | None = None
    track: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    category: str | None = None
    position_age_s: float | None = None
    distance_nm: float | None = None
    bearing: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Aircraft":
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

    @property
    def distance_km(self) -> float | None:
        """Distance to the observer in kilometres, if known."""
        if self.distance_nm is None:
            return None
        return self.distance_nm * KM_PER_NM

    @property
    def altitude_m(self) -> int | None:
        """Barometric altitude in metres, if known."""
        if self.altitude_ft is None:
            return None
        return int(self.altitude_ft * M_PER_FT)

    @property
    def airline_code(self) -> str | None:
        """The leading three letters of the callsign.

        For airline flights this is the ICAO operator code (RYR, DLH).
        For private aircraft the callsign is the registration, so the
        result is meaningless here and only becomes useful once it is
        matched against a list of known operators.
        """
        if not self.callsign or len(self.callsign) < 4:
            return None
        prefix = self.callsign[:3]
        return prefix if prefix.isalpha() else None


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


def _fmt(value, spec: str = "", empty: str = "-") -> str:
    """Format a value, or return a placeholder when it is None."""
    return format(value, spec) if value is not None else empty


if __name__ == "__main__":
    from planeframe.sources.airplanes_live import load_sample

    result = load_sample("data/samples/20260802-192448.json")
    planes = aircraft_from_response(result)

    print(f"{len(planes)} aircraft parsed\n")
    print(f"{'CALLSIGN':<10} {'TYPE':<6} {'OPER':<5} {'ALT FT':>7} {'KM':>7}")
    print("-" * 40)

    for plane in planes:
        print(
            f"{_fmt(plane.callsign):<10} "
            f"{_fmt(plane.type_code):<6} "
            f"{_fmt(plane.airline_code):<5} "
            f"{_fmt(plane.altitude_ft):>7} "
            f"{_fmt(plane.distance_km, '.1f'):>7}"
        )