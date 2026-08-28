from dataclasses import dataclass
from typing import List, Optional


# ============================================================
# WAYPOINT
# ============================================================

@dataclass
class Waypoint:

    index: int

    latitude: float

    longitude: float

    altitude: float

    speed: float = 5.0

    hold_time: float = 0.0

    name: str = ""
    command: int = 16
    acceptance_radius: float = 0.0
    yaw: float = 0.0
    source_seq: int = -1


# ============================================================
# MISSION
# ============================================================

class Mission:

    def __init__(self):

        self.waypoints: List[Waypoint] = []

        # Zero-based index.
        #
        # -1 = no waypoint selected
        #  0 = first waypoint
        #  1 = second waypoint
        # ...
        self.current_index: int = -1

        self.started: bool = False

        self.finished: bool = False

    # ========================================================
    # ADD WAYPOINT
    # ========================================================

    def add_waypoint(
        self,
        latitude: float,
        longitude: float,
        altitude: float,
        speed: float = 5.0,
        hold_time: float = 0.0,
        name: str = "",
        command: int = 16,
        acceptance_radius: float = 0.0,
        yaw: float = 0.0,
    ) -> Waypoint:

        waypoint = Waypoint(
            index=len(self.waypoints) + 1,
            latitude=float(latitude),
            longitude=float(longitude),
            altitude=float(altitude),
            speed=max(
                0.0,
                float(speed),
            ),
            hold_time=max(
                0.0,
                float(hold_time),
            ),
            name=str(name),
            command=int(command),
            acceptance_radius=max(0.0, float(acceptance_radius)),
            yaw=float(yaw) % 360.0,
            source_seq=len(self.waypoints),
        )

        self.waypoints.append(
            waypoint
        )

        # Adding a waypoint after a completed mission
        # makes the mission available again.
        self.finished = False

        return waypoint

    # ========================================================
    # REMOVE WAYPOINT
    # ========================================================

    def remove_waypoint(
        self,
        index: int,
    ) -> bool:

        if index < 1:
            return False

        if index > len(
            self.waypoints
        ):
            return False

        removed_index = (
            index - 1
        )

        self.waypoints.pop(
            removed_index
        )

        self._reindex()

        # ----------------------------------------------------
        # No waypoints left
        # ----------------------------------------------------

        if not self.waypoints:

            self.current_index = -1

            self.started = False

            self.finished = False

            return True

        # ----------------------------------------------------
        # Current waypoint was removed
        # ----------------------------------------------------

        if (
            self.current_index
            > removed_index
        ):

            self.current_index -= 1

        elif (
            self.current_index
            == removed_index
        ):

            # Keep the index inside the valid range.
            self.current_index = min(
                self.current_index,
                len(self.waypoints) - 1,
            )

        # ----------------------------------------------------
        # If the mission is running, it is no longer
        # automatically considered finished.
        # ----------------------------------------------------

        if self.started:

            self.finished = False

        return True

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(self):

        self.waypoints.clear()

        self.current_index = -1

        self.started = False

        self.finished = False

    # ========================================================
    # RESET
    #
    # Keep the waypoints but reset mission execution.
    # ========================================================

    def reset(self):

        self.current_index = -1

        self.started = False

        self.finished = False

    # ========================================================
    # REINDEX
    # ========================================================

    def _reindex(self):

        for i, waypoint in enumerate(
            self.waypoints,
            start=1,
        ):

            waypoint.index = i

    # ========================================================
    # COUNT
    # ========================================================

    def count(self) -> int:

        return len(
            self.waypoints
        )

    # ========================================================
    # GET WAYPOINT
    # ========================================================

    def get_waypoint(
        self,
        index: int,
    ) -> Optional[Waypoint]:

        if index < 1:

            return None

        if index > len(
            self.waypoints
        ):

            return None

        return self.waypoints[
            index - 1
        ]

    # ========================================================
    # CURRENT WAYPOINT
    # ========================================================

    def get_current_waypoint(
        self,
    ) -> Optional[Waypoint]:

        if (
            self.current_index < 0
            or
            self.current_index
            >= len(self.waypoints)
        ):

            return None

        return self.waypoints[
            self.current_index
        ]

    # ========================================================
    # START
    # ========================================================

    def start(self) -> bool:

        if not self.waypoints:

            return False

        self.current_index = 0

        self.started = True

        self.finished = False

        return True

    # ========================================================
    # NEXT WAYPOINT
    # ========================================================

    def next_waypoint(
        self,
    ) -> Optional[Waypoint]:

        if not self.waypoints:

            return None

        # ----------------------------------------------------
        # Mission wasn't started.
        #
        # Start from waypoint 1.
        # ----------------------------------------------------

        if self.current_index < 0:

            self.current_index = 0

            self.started = True

            self.finished = False

            return self.get_current_waypoint()

        # ----------------------------------------------------
        # Already at last waypoint.
        #
        # Do NOT return None here just because we are
        # currently on the last waypoint.
        #
        # The navigator decides that the last waypoint
        # has been reached and then finishes the mission.
        # ----------------------------------------------------

        if (
            self.current_index
            >= len(self.waypoints) - 1
        ):

            self.finished = True

            return None

        # ----------------------------------------------------
        # Move to next waypoint.
        # ----------------------------------------------------

        self.current_index += 1

        self.started = True

        self.finished = False

        return self.get_current_waypoint()

    # ========================================================
    # IS STARTED
    # ========================================================

    def is_started(self) -> bool:

        return self.started

    # ========================================================
    # IS FINISHED
    # ========================================================

    def is_finished(self) -> bool:

        return self.finished

    # ========================================================
    # IS LAST WAYPOINT
    # ========================================================

    def is_last_waypoint(self) -> bool:

        if not self.waypoints:

            return False

        if self.current_index < 0:

            return False

        return (
            self.current_index
            == len(self.waypoints) - 1
        )

    # ========================================================
    # GET CURRENT INDEX
    #
    # Returns MAVLink-style waypoint number:
    # 1, 2, 3...
    #
    # Returns 0 if no waypoint is active.
    # ========================================================

    def get_current_index(self) -> int:

        if self.current_index < 0:

            return 0

        return (
            self.current_index + 1
        )

    # ========================================================
    # GET ALL
    # ========================================================

    def get_all(
        self,
    ) -> List[Waypoint]:

        return list(
            self.waypoints
        )