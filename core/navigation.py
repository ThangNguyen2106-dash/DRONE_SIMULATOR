"""
Navigation module for Drone Simulator.

Responsibilities:
- Calculate distance between two GPS coordinates
- Calculate bearing between two GPS coordinates
- Calculate destination point
- Calculate navigation error
- Determine whether the drone has reached a target
- Provide simple navigation commands

This module does NOT control the drone motor/physics.
Flight dynamics will be implemented in simulation/flight_model.py.
"""

import math
from dataclasses import dataclass
from typing import Optional


# ============================================================
# Constants
# ============================================================

EARTH_RADIUS_M = 6_371_000.0


# ============================================================
# Data classes
# ============================================================

@dataclass
class GPSPoint:
    """GPS coordinate."""

    lat: float
    lon: float
    alt: float = 0.0


@dataclass
class NavigationResult:
    """Navigation calculation result."""

    distance_m: float
    bearing_deg: float
    altitude_error_m: float
    reached: bool


# ============================================================
# Navigation
# ============================================================

class Navigation:
    """
    Navigation system for the drone simulator.

    This class is responsible only for navigation mathematics
    and high-level navigation decisions.

    It does not simulate physical movement.
    """

    def __init__(
        self,
        arrival_radius_m: float = 2.0,
        altitude_tolerance_m: float = 1.0,
    ):
        self.arrival_radius_m = float(arrival_radius_m)
        self.altitude_tolerance_m = float(altitude_tolerance_m)

        self.current_position = GPSPoint(
            lat=0.0,
            lon=0.0,
            alt=0.0,
        )

        self.target_position: Optional[GPSPoint] = None

    # ========================================================
    # Position
    # ========================================================

    def set_current_position(
        self,
        lat: float,
        lon: float,
        alt: float = 0.0,
    ) -> None:
        """
        Update current drone position.
        """

        self.current_position = GPSPoint(
            lat=float(lat),
            lon=float(lon),
            alt=float(alt),
        )

    def set_target(
        self,
        lat: float,
        lon: float,
        alt: float = 0.0,
    ) -> None:
        """
        Set navigation target.
        """

        self.target_position = GPSPoint(
            lat=float(lat),
            lon=float(lon),
            alt=float(alt),
        )

    def clear_target(self) -> None:
        """Remove current navigation target."""

        self.target_position = None

    # ========================================================
    # GPS calculations
    # ========================================================

    @staticmethod
    def distance_m(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate great-circle distance between two GPS points.

        Returns:
            Distance in meters.
        """

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)

        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2.0) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(delta_lon / 2.0) ** 2
        )

        a = max(0.0, min(1.0, a))

        c = 2.0 * math.atan2(
            math.sqrt(a),
            math.sqrt(1.0 - a),
        )

        return EARTH_RADIUS_M * c

    @staticmethod
    def bearing_deg(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate initial bearing from point 1 to point 2.

        Returns:
            Bearing in degrees [0, 360).

        Convention:
            0   = North
            90  = East
            180 = South
            270 = West
        """

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)

        delta_lon = math.radians(lon2 - lon1)

        x = (
            math.sin(delta_lon)
            * math.cos(lat2_rad)
        )

        y = (
            math.cos(lat1_rad)
            * math.sin(lat2_rad)
            - math.sin(lat1_rad)
            * math.cos(lat2_rad)
            * math.cos(delta_lon)
        )

        bearing = math.degrees(
            math.atan2(x, y)
        )

        return (bearing + 360.0) % 360.0

    # ========================================================
    # Altitude
    # ========================================================

    @staticmethod
    def altitude_error(
        current_alt: float,
        target_alt: float,
    ) -> float:
        """
        Calculate altitude error.

        Positive:
            Drone needs to climb.

        Negative:
            Drone needs to descend.
        """

        return float(target_alt) - float(current_alt)

    # ========================================================
    # Navigation status
    # ========================================================

    def get_navigation_result(self) -> Optional[NavigationResult]:
        """
        Calculate current navigation status.

        Returns:
            NavigationResult or None if no target exists.
        """

        if self.target_position is None:
            return None

        current = self.current_position
        target = self.target_position

        distance = self.distance_m(
            current.lat,
            current.lon,
            target.lat,
            target.lon,
        )

        bearing = self.bearing_deg(
            current.lat,
            current.lon,
            target.lat,
            target.lon,
        )

        altitude_error = self.altitude_error(
            current.alt,
            target.alt,
        )

        reached = (
            distance <= self.arrival_radius_m
            and abs(altitude_error)
            <= self.altitude_tolerance_m
        )

        return NavigationResult(
            distance_m=distance,
            bearing_deg=bearing,
            altitude_error_m=altitude_error,
            reached=reached,
        )

    # ========================================================
    # Target status
    # ========================================================

    def has_target(self) -> bool:
        """Return True when a target exists."""

        return self.target_position is not None

    def is_target_reached(self) -> bool:
        """Return True when the drone has reached its target."""

        result = self.get_navigation_result()

        if result is None:
            return False

        return result.reached

    # ========================================================
    # Direction
    # ========================================================

    def get_distance_to_target(self) -> Optional[float]:
        """Return distance to target in meters."""

        result = self.get_navigation_result()

        if result is None:
            return None

        return result.distance_m

    def get_bearing_to_target(self) -> Optional[float]:
        """Return bearing to target in degrees."""

        result = self.get_navigation_result()

        if result is None:
            return None

        return result.bearing_deg

    def get_altitude_error(self) -> Optional[float]:
        """Return altitude error in meters."""

        result = self.get_navigation_result()

        if result is None:
            return None

        return result.altitude_error_m

    # ========================================================
    # Utility
    # ========================================================

    @staticmethod
    def normalize_angle(angle_deg: float) -> float:
        """
        Normalize angle to [-180, 180).

        Example:

            350 -> -10
            10  -> 10
            180 -> -180
        """

        return (angle_deg + 180.0) % 360.0 - 180.0

    @staticmethod
    def heading_error(
        current_heading_deg: float,
        target_bearing_deg: float,
    ) -> float:
        """
        Calculate shortest heading error.

        Positive:
            Turn right / clockwise.

        Negative:
            Turn left / counter-clockwise.
        """

        error = (
            target_bearing_deg
            - current_heading_deg
        )

        return Navigation.normalize_angle(error)

    def get_heading_error(
        self,
        current_heading_deg: float,
    ) -> Optional[float]:
        """
        Calculate heading error from current drone heading
        to target.
        """

        bearing = self.get_bearing_to_target()

        if bearing is None:
            return None

        return self.heading_error(
            current_heading_deg,
            bearing,
        )


# ============================================================
# Simple helper functions
# ============================================================

def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Standalone distance calculation."""

    return Navigation.distance_m(
        lat1,
        lon1,
        lat2,
        lon2,
    )


def calculate_bearing(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Standalone bearing calculation."""

    return Navigation.bearing_deg(
        lat1,
        lon1,
        lat2,
        lon2,
    )