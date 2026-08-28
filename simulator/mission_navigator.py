from typing import Optional

from core.navigation import Navigation
from simulator.mission import Mission, Waypoint


class MissionNavigator:

    def __init__(
        self,
        mission: Mission,
        navigation: Navigation,
    ):

        self.mission = mission

        self.navigation = navigation

        self.active = False

        self.completed = False

    # ========================================================
    # START
    # ========================================================

    def start(self) -> bool:

        if self.mission.count() == 0:

            return False

        # ----------------------------------------------------
        # Resume from where the mission was stopped.
        #
        # STOP does not reset mission.current_index, so if
        # the mission was already in progress (and not
        # finished), continue from the current waypoint
        # instead of restarting from waypoint 1.
        # ----------------------------------------------------

        if (
            self.mission.is_started()
            and not self.mission.is_finished()
            and self.mission.get_current_waypoint()
            is not None
        ):

            self.active = True

            self.completed = False

            self._set_current_waypoint_target()

            return True

        # ----------------------------------------------------
        # Reset previous execution state.
        # ----------------------------------------------------

        self.active = False

        self.completed = False

        self.navigation.clear_target()

        # ----------------------------------------------------
        # Start mission from waypoint 1.
        # ----------------------------------------------------

        if not self.mission.start():

            return False

        self.active = True

        self.completed = False

        self._set_current_waypoint_target()

        return True

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.active = False

        # ----------------------------------------------------
        # Do not mark mission as completed.
        #
        # STOP means paused/stopped, not finished.
        # ----------------------------------------------------

        self.completed = False

    # ========================================================
    # RESET
    # ========================================================

    def reset(self):

        self.active = False

        self.completed = False

        self.mission.reset()

        self.navigation.clear_target()

    # ========================================================
    # UPDATE POSITION
    # ========================================================

    def update_position(
        self,
        lat: float,
        lon: float,
        alt: float,
    ):

        self.navigation.set_current_position(
            lat=lat,
            lon=lon,
            alt=alt,
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        lat: float,
        lon: float,
        alt: float,
    ) -> Optional[Waypoint]:

        # ----------------------------------------------------
        # No active mission.
        # ----------------------------------------------------

        if not self.active:

            return (
                self.mission
                .get_current_waypoint()
            )

        # ----------------------------------------------------
        # Already completed.
        # ----------------------------------------------------

        if self.completed:

            return None

        # ----------------------------------------------------
        # Update current drone position.
        # ----------------------------------------------------

        self.update_position(
            lat=lat,
            lon=lon,
            alt=alt,
        )

        # ----------------------------------------------------
        # Get current waypoint.
        # ----------------------------------------------------

        waypoint = (
            self.mission
            .get_current_waypoint()
        )

        if waypoint is None:

            self._finish_mission()

            return None

        # ----------------------------------------------------
        # Check whether current waypoint has been reached.
        # ----------------------------------------------------

        if self.navigation.is_target_reached():

            return self._advance()

        # ----------------------------------------------------
        # Continue travelling toward current waypoint.
        # ----------------------------------------------------

        return waypoint

    # ========================================================
    # ADVANCE
    # ========================================================

    def _advance(
        self,
    ) -> Optional[Waypoint]:

        # ----------------------------------------------------
        # Current waypoint has been reached.
        #
        # If it is the LAST waypoint, the mission is finished.
        # ----------------------------------------------------

        if self.mission.is_last_waypoint():

            self._finish_mission()

            return None

        # ----------------------------------------------------
        # Move to next waypoint.
        # ----------------------------------------------------

        waypoint = (
            self.mission.next_waypoint()
        )

        if waypoint is None:

            self._finish_mission()

            return None

        # ----------------------------------------------------
        # Set navigation target.
        # ----------------------------------------------------

        self._set_current_waypoint_target()

        return waypoint

    # ========================================================
    # FINISH
    # ========================================================

    def _finish_mission(self):

        self.active = False

        self.completed = True

        # ----------------------------------------------------
        # Tell Mission that execution is finished.
        # ----------------------------------------------------

        self.mission.finished = True

        # ----------------------------------------------------
        # Clear navigation target.
        # ----------------------------------------------------

        self.navigation.clear_target()

    # ========================================================
    # SET CURRENT TARGET
    # ========================================================

    def _set_current_waypoint_target(self):

        waypoint = (
            self.mission
            .get_current_waypoint()
        )

        if waypoint is None:

            self.navigation.clear_target()

            return

        self.navigation.set_target(
            lat=waypoint.latitude,
            lon=waypoint.longitude,
            alt=waypoint.altitude,
        )

    # ========================================================
    # CURRENT WAYPOINT
    # ========================================================

    def get_current_waypoint(
        self,
    ) -> Optional[Waypoint]:

        return (
            self.mission
            .get_current_waypoint()
        )

    # ========================================================
    # CURRENT NAVIGATION
    # ========================================================

    def get_navigation_result(self):

        return (
            self.navigation
            .get_navigation_result()
        )

    # ========================================================
    # STATUS
    # ========================================================

    def is_active(self) -> bool:

        return self.active

    # ========================================================

    def is_completed(self) -> bool:

        return self.completed

    # ========================================================

    def has_waypoint(self) -> bool:

        return (
            self.mission
            .get_current_waypoint()
            is not None
        )