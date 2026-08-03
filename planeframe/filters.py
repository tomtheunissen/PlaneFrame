from planeframe.models import Aircraft


def remove_grounded(aircraft: list[Aircraft]) -> list[Aircraft]:
    """Drop aircraft that are on the ground."""
    return [plane for plane in aircraft if not plane.on_ground]



if __name__ == "__main__":
    from planeframe.sources.airplanes_live import load_sample
    from planeframe.models import aircraft_from_response

    result = load_sample("data/samples/20260802-192448.json")
    planes = aircraft_from_response(result)

    print(remove_grounded(planes))