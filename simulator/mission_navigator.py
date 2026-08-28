from typing import Optional

from core.navigation import Navigation
from simulator.mission import Mission, Waypoint


class MissionNavigator:

    def __init__(self, mission: Mission, navigation: Navigation):
        self.mission = mission
        self.navigation = navigation
        self.active = False
        self.completed = False
        self.hold_started_at: Optional[float] = None
        self.default_arrival_radius = navigation.arrival_radius_m

    def start(self) -> bool:
        if self.mission.count() == 0:
            return False
        self.active = False
        self.completed = False
        self.hold_started_at = None
        self.navigation.clear_target()
        if not self.mission.start():
            return False
        self.active = True
        self._set_current_waypoint_target()
        return True

    def stop(self):
        self.active = False
        self.completed = False
        self.hold_started_at = None

    def reset(self):
        self.active = False
        self.completed = False
        self.hold_started_at = None
        self.mission.reset()
        self.navigation.clear_target()

    def update_position(self, lat: float, lon: float, alt: float):
        self.navigation.set_current_position(lat=lat, lon=lon, alt=alt)

    def update(self, lat: float, lon: float, alt: float, sim_time: float = 0.0) -> Optional[Waypoint]:
        if not self.active:
            return self.mission.get_current_waypoint()
        if self.completed:
            return None

        self.update_position(lat, lon, alt)
        sim_time = float(sim_time)
        waypoint = self.mission.get_current_waypoint()
        if waypoint is None:
            self._finish_mission()
            return None

        # LAND is special: do not finish while still ~1 m above ground.
        reached = self._is_waypoint_reached(waypoint)

        if reached:
            hold = max(0.0, float(getattr(waypoint, "hold_time", 0.0)))
            if hold > 0.0:
                if self.hold_started_at is None:
                    self.hold_started_at = sim_time
                
                if sim_time - self.hold_started_at < hold:
                    return waypoint
            return self._advance()

        self.hold_started_at = None
        return waypoint

    def _is_waypoint_reached(self, waypoint: Waypoint) -> bool:
        result = self.navigation.get_navigation_result()
        if result is None:
            return False

        command = int(getattr(waypoint, "command", 16))
        land_command = 21  # MAV_CMD_NAV_LAND

        if command == land_command:
            # Land only completes after reaching the XY target AND ground.
            return result.distance_m <= self.navigation.arrival_radius_m and self.navigation.current_position.alt <= 0.10

        return result.reached

    def _advance(self) -> Optional[Waypoint]:
        self.hold_started_at = None
        if self.mission.is_last_waypoint():
            self._finish_mission()
            return None
        waypoint = self.mission.next_waypoint()
        if waypoint is None:
            self._finish_mission()
            return None
        self._set_current_waypoint_target()
        return waypoint

    def _finish_mission(self):
        self.active = False
        self.completed = True
        self.mission.finished = True
        self.navigation.clear_target()
        self.navigation.arrival_radius_m = self.default_arrival_radius

    def _set_current_waypoint_target(self):
        waypoint = self.mission.get_current_waypoint()
        if waypoint is None:
            self.navigation.clear_target()
            return

        radius = float(getattr(waypoint, "acceptance_radius", 0.0))
        self.navigation.arrival_radius_m = radius if radius > 0.0 else self.default_arrival_radius
        self.navigation.set_target(
            lat=waypoint.latitude,
            lon=waypoint.longitude,
            alt=waypoint.altitude,
        )

    def get_current_waypoint(self) -> Optional[Waypoint]:
        return self.mission.get_current_waypoint()

    def get_navigation_result(self):
        return self.navigation.get_navigation_result()

    def is_active(self) -> bool:
        return self.active

    def is_completed(self) -> bool:
        return self.completed

    def has_waypoint(self) -> bool:
        return self.mission.get_current_waypoint() is not None
