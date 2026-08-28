import math
from dataclasses import dataclass
from typing import Optional


EARTH_RADIUS_M = 6_371_000.0


@dataclass
class GPSPoint:
    lat: float
    lon: float
    alt: float = 0.0


@dataclass
class NavigationResult:
    distance_m: float
    bearing_deg: float
    altitude_error_m: float
    reached: bool


class Navigation:

    def __init__(
        self,
        arrival_radius_m: float = 2.0,
        altitude_tolerance_m: float = 1.0,
    ):

        self.arrival_radius_m = max(
            0.01,
            float(arrival_radius_m),
        )

        self.altitude_tolerance_m = max(
            0.0,
            float(altitude_tolerance_m),
        )

        self.current_position = GPSPoint(
            0.0,
            0.0,
            0.0,
        )

        self.target_position: Optional[
            GPSPoint
        ] = None

    # ========================================================
    # VALIDATE GPS
    # ========================================================

    @staticmethod
    def _validate_latitude(
        latitude: float,
    ) -> float:

        latitude = float(latitude)

        return max(
            -90.0,
            min(
                90.0,
                latitude,
            ),
        )

    # ========================================================

    @staticmethod
    def _normalize_longitude(
        longitude: float,
    ) -> float:

        longitude = float(longitude)

        return (
            longitude + 180.0
        ) % 360.0 - 180.0

    # ========================================================
    # CURRENT POSITION
    # ========================================================

    def set_current_position(
        self,
        lat: float,
        lon: float,
        alt: float = 0.0,
    ):

        self.current_position = GPSPoint(
            lat=self._validate_latitude(
                lat
            ),
            lon=self._normalize_longitude(
                lon
            ),
            alt=float(alt),
        )

    # ========================================================
    # GET CURRENT POSITION
    # ========================================================

    def get_current_position(
        self,
    ) -> GPSPoint:

        return GPSPoint(
            lat=self.current_position.lat,
            lon=self.current_position.lon,
            alt=self.current_position.alt,
        )

    # ========================================================
    # TARGET POSITION
    # ========================================================

    def set_target(
        self,
        lat: float,
        lon: float,
        alt: float = 0.0,
    ):

        self.target_position = GPSPoint(
            lat=self._validate_latitude(
                lat
            ),
            lon=self._normalize_longitude(
                lon
            ),
            alt=float(alt),
        )

    # ========================================================
    # GET TARGET
    # ========================================================

    def get_target(
        self,
    ) -> Optional[GPSPoint]:

        if self.target_position is None:

            return None

        return GPSPoint(
            lat=self.target_position.lat,
            lon=self.target_position.lon,
            alt=self.target_position.alt,
        )

    # ========================================================
    # CLEAR TARGET
    # ========================================================

    def clear_target(self):

        self.target_position = None

    # ========================================================
    # HAS TARGET
    # ========================================================

    def has_target(self) -> bool:

        return (
            self.target_position is not None
        )

    # ========================================================
    # DISTANCE
    #
    # Haversine distance on Earth's surface.
    # ========================================================

    @staticmethod
    def distance_m(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:

        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

        lat1_rad = math.radians(
            lat1
        )

        lat2_rad = math.radians(
            lat2
        )

        delta_lat = math.radians(
            lat2 - lat1
        )

        # Normalize longitude difference.
        delta_lon_deg = (
            lon2 - lon1
        )

        delta_lon_deg = (
            delta_lon_deg + 180.0
        ) % 360.0 - 180.0

        delta_lon = math.radians(
            delta_lon_deg
        )

        a = (
            math.sin(
                delta_lat / 2.0
            ) ** 2
            +
            math.cos(lat1_rad)
            *
            math.cos(lat2_rad)
            *
            math.sin(
                delta_lon / 2.0
            ) ** 2
        )

        # Floating point protection.
        a = max(
            0.0,
            min(
                1.0,
                a,
            ),
        )

        c = 2.0 * math.atan2(
            math.sqrt(a),
            math.sqrt(
                1.0 - a
            ),
        )

        return (
            EARTH_RADIUS_M * c
        )

    # ========================================================
    # 3D DISTANCE
    #
    # Surface distance + altitude difference.
    # ========================================================

    @staticmethod
    def distance_3d_m(
        lat1: float,
        lon1: float,
        alt1: float,
        lat2: float,
        lon2: float,
        alt2: float,
    ) -> float:

        horizontal = (
            Navigation.distance_m(
                lat1,
                lon1,
                lat2,
                lon2,
            )
        )

        vertical = (
            float(alt2)
            - float(alt1)
        )

        return math.sqrt(
            horizontal ** 2
            +
            vertical ** 2
        )

    # ========================================================
    # BEARING
    #
    # 0   = North
    # 90  = East
    # 180 = South
    # 270 = West
    # ========================================================

    @staticmethod
    def bearing_deg(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:

        lat1_rad = math.radians(
            float(lat1)
        )

        lat2_rad = math.radians(
            float(lat2)
        )

        delta_lon_deg = (
            float(lon2)
            - float(lon1)
        )

        delta_lon_deg = (
            delta_lon_deg + 180.0
        ) % 360.0 - 180.0

        delta_lon = math.radians(
            delta_lon_deg
        )

        x = (
            math.sin(delta_lon)
            * math.cos(lat2_rad)
        )

        y = (
            math.cos(lat1_rad)
            * math.sin(lat2_rad)
            -
            math.sin(lat1_rad)
            * math.cos(lat2_rad)
            * math.cos(delta_lon)
        )

        # Same coordinates -> no meaningful bearing.
        if (
            abs(x) < 1e-12
            and
            abs(y) < 1e-12
        ):

            return 0.0

        bearing = math.degrees(
            math.atan2(
                x,
                y,
            )
        )

        return (
            bearing + 360.0
        ) % 360.0

    # ========================================================
    # ALTITUDE ERROR
    # ========================================================

    @staticmethod
    def altitude_error(
        current_alt: float,
        target_alt: float,
    ) -> float:

        return (
            float(target_alt)
            - float(current_alt)
        )

    # ========================================================
    # NAVIGATION RESULT
    # ========================================================

    def get_navigation_result(
        self,
    ) -> Optional[NavigationResult]:

        if self.target_position is None:

            return None

        current = (
            self.current_position
        )

        target = (
            self.target_position
        )

        # ----------------------------------------------------
        # Horizontal distance
        # ----------------------------------------------------

        distance = (
            self.distance_m(
                current.lat,
                current.lon,
                target.lat,
                target.lon,
            )
        )

        # ----------------------------------------------------
        # Bearing
        # ----------------------------------------------------

        bearing = (
            self.bearing_deg(
                current.lat,
                current.lon,
                target.lat,
                target.lon,
            )
        )

        # ----------------------------------------------------
        # Altitude error
        # ----------------------------------------------------

        altitude_error = (
            self.altitude_error(
                current.alt,
                target.alt,
            )
        )

        # ----------------------------------------------------
        # Reached condition
        #
        # BOTH horizontal and altitude requirements
        # must be satisfied.
        # ----------------------------------------------------

        horizontal_reached = (
            distance
            <= self.arrival_radius_m
        )

        altitude_reached = (
            abs(
                altitude_error
            )
            <= self.altitude_tolerance_m
        )

        reached = (
            horizontal_reached
            and
            altitude_reached
        )

        return NavigationResult(
            distance_m=distance,
            bearing_deg=bearing,
            altitude_error_m=altitude_error,
            reached=reached,
        )

    # ========================================================
    # TARGET STATUS
    # ========================================================

    def is_target_reached(
        self,
    ) -> bool:

        result = (
            self.get_navigation_result()
        )

        if result is None:

            return False

        return result.reached

    # ========================================================
    # ALIAS
    # ========================================================

    def target_reached(
        self,
    ) -> bool:

        return self.is_target_reached()

    # ========================================================
    # DISTANCE TO TARGET
    # ========================================================

    def get_distance_to_target(
        self,
    ) -> Optional[float]:

        result = (
            self.get_navigation_result()
        )

        if result is None:

            return None

        return result.distance_m

    # ========================================================
    # BEARING TO TARGET
    # ========================================================

    def get_bearing_to_target(
        self,
    ) -> Optional[float]:

        result = (
            self.get_navigation_result()
        )

        if result is None:

            return None

        return result.bearing_deg

    # ========================================================
    # ALTITUDE ERROR
    # ========================================================

    def get_altitude_error(
        self,
    ) -> Optional[float]:

        result = (
            self.get_navigation_result()
        )

        if result is None:

            return None

        return result.altitude_error_m

    # ========================================================
    # HEADING ERROR
    # ========================================================

    @staticmethod
    def normalize_angle(
        angle_deg: float,
    ) -> float:

        return (
            float(angle_deg)
            + 180.0
        ) % 360.0 - 180.0

    # ========================================================

    @staticmethod
    def heading_error(
        current_heading_deg: float,
        target_bearing_deg: float,
    ) -> float:

        error = (
            float(target_bearing_deg)
            -
            float(current_heading_deg)
        )

        return (
            Navigation.normalize_angle(
                error
            )
        )