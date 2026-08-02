class Aircraft:
    def __init__(
            self,
            icao,
            callsign=None,
            registration=None,
            type_code=None,
            description=None,
            altitude_ft=None,
            on_ground=False,
            ground_speed_kt=None,
            track=None,
            latitude=None,
            longitude=None,
            category=None,
            position_age_s=None,
            distance_nm=None,
            bearing=None,
            ):
        
        self.icao = icao
        self.callsign = callsign
        self.registration = registration
        self.type_code = type_code
        self.description = description
        self.altitude_ft = altitude_ft
        self.on_ground = on_ground
        self.ground_speed_kt = ground_speed_kt
        self.track = track
        self.latitude = latitude
        self.longitude = longitude
        self.category = category
        self.position_age_s = position_age_s
        self.distance_nm = distance_nm
        self.bearing = bearing

a = Aircraft(icao="8964b5", callsign="UAE70M")
print(a.callsign)
print(a)