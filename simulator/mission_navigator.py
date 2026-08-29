from typing import Optional

from core.navigation import Navigation
from simulator.mission import Mission, Waypoint
from simulator.mission_tasks import MissionTask, MissionTaskExecutor


class MissionNavigator:
    """Navigation + stateful mission task execution."""

    def __init__(self, mission: Mission, navigation: Navigation):
        self.mission = mission
        self.navigation = navigation
        self.active = False
        self.completed = False
        self.hold_started_at: Optional[float] = None
        self.default_arrival_radius = navigation.arrival_radius_m
        self.task_executor = MissionTaskExecutor()
        self.last_task_result = None
        self._task_index = 0
        self._tasks_started_for_index = -1

    def start(self) -> bool:
        if self.mission.count() == 0:
            return False
        self.active = False
        self.completed = False
        self.hold_started_at = None
        self.last_task_result = None
        self._task_index = 0
        self._tasks_started_for_index = -1
        self.task_executor.reset()
        self.navigation.clear_target()
        if not self.mission.start():
            return False
        self.active = True
        self._set_current_waypoint_target()
        print(f"[MISSION] START count={self.mission.count()}")
        return True

    def stop(self):
        self.active = False
        self.completed = False
        self.hold_started_at = None
        self.task_executor.reset()

    def reset(self):
        self.active = False
        self.completed = False
        self.hold_started_at = None
        self.last_task_result = None
        self._task_index = 0
        self._tasks_started_for_index = -1
        self.task_executor.reset()
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

        if not self._is_waypoint_reached(waypoint):
            self.hold_started_at = None
            return waypoint

        tasks = list(getattr(waypoint, "tasks", []) or [])
        if self._tasks_started_for_index != waypoint.index:
            self._tasks_started_for_index = waypoint.index
            self._task_index = 0
            self.task_executor.reset()
            print(f"[MISSION] WP{waypoint.index} REACHED")

        # Execute tasks sequentially. A RUNNING task blocks mission advance.
        while self._task_index < len(tasks):
            task = tasks[self._task_index]
            result = self.task_executor.execute(task, waypoint.index, sim_time)
            self.last_task_result = result
            if result.get("status") != "DONE":
                return waypoint

            # Terminal task such as RTL transfers control to the drone
            # flight controller. Do not call _advance(), because that
            # would clear the HOME target that RTL just configured.
            metadata = result.get("metadata") or {}
            if metadata.get("terminal"):
                self.active = False
                self.completed = True
                self.mission.finished = True
                self.hold_started_at = None
                self._task_index = 0
                self._tasks_started_for_index = -1
                print(f"[MISSION] TERMINAL TASK -> {result.get('task', 'ACTION')}")
                return waypoint

            self._task_index += 1

        # Waypoint delay / LOITER_TIME.
        hold = max(0.0, float(getattr(waypoint, "hold_time", 0.0)))
        if hold > 0.0:
            if self.hold_started_at is None:
                self.hold_started_at = sim_time
                print(f"[MISSION] WP{waypoint.index} HOLD START {hold:.1f}s")
            elapsed = sim_time - self.hold_started_at
            if elapsed < hold:
                return waypoint
            print(f"[MISSION] WP{waypoint.index} HOLD COMPLETE")

        return self._advance()

    def _is_waypoint_reached(self, waypoint: Waypoint) -> bool:
        result = self.navigation.get_navigation_result()
        if result is None:
            return False
        if int(getattr(waypoint, "command", 16)) == 21:
            return result.distance_m <= self.navigation.arrival_radius_m and self.navigation.current_position.alt <= 0.10
        return result.reached

    def _advance(self) -> Optional[Waypoint]:
        self.hold_started_at = None
        self._task_index = 0
        self._tasks_started_for_index = -1
        self.task_executor.reset()
        if self.mission.is_last_waypoint():
            self._finish_mission()
            return None
        waypoint = self.mission.next_waypoint()
        if waypoint is None:
            self._finish_mission()
            return None
        self._set_current_waypoint_target()
        print(f"[MISSION] NEXT WP{waypoint.index}")
        return waypoint

    def _finish_mission(self):
        self.active = False
        self.completed = True
        self.mission.finished = True
        self.navigation.clear_target()
        self.navigation.arrival_radius_m = self.default_arrival_radius
        print("[MISSION] COMPLETE")

    def _set_current_waypoint_target(self):
        waypoint = self.mission.get_current_waypoint()
        if waypoint is None:
            self.navigation.clear_target()
            return
        radius = float(getattr(waypoint, "acceptance_radius", 0.0))
        self.navigation.arrival_radius_m = radius if radius > 0.0 else self.default_arrival_radius
        self.navigation.set_target(lat=waypoint.latitude, lon=waypoint.longitude, alt=waypoint.altitude)

    def attach_task(self, waypoint_index: int, task: MissionTask) -> bool:
        waypoint = self.mission.get_waypoint(int(waypoint_index))
        if waypoint is None:
            return False
        waypoint.tasks.append(task)
        return True

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
