from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MissionTask:
    """A simulator-side action executed at a mission waypoint."""
    task_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


class MissionTaskExecutor:
    """Stateful executor: a task can remain RUNNING across simulation ticks."""

    def __init__(self, drone=None):
        self.drone = drone
        self.last_task: Optional[MissionTask] = None
        self.last_result: Optional[Dict[str, Any]] = None
        self.history: List[Dict[str, Any]] = []
        self._capture_index = 0
        self._active_task: Optional[MissionTask] = None
        self._active_started_at: Optional[float] = None
        self._active_wp = -1

    def reset(self):
        self._active_task = None
        self._active_started_at = None
        self._active_wp = -1

    def execute(self, task: MissionTask, waypoint_index: int, sim_time: float) -> Dict[str, Any]:
        """Start/update a task. Returns status RUNNING or DONE.

        Special terminal actions (for example RTL) return metadata
        ``terminal=True`` so MissionNavigator can transfer control to
        the flight controller without destroying the new navigation target.
        """
        if self._active_task is not task or self._active_wp != waypoint_index:
            self._active_task = task
            self._active_wp = waypoint_index
            self._active_started_at = float(sim_time)
            self.last_task = task

            task_type = str(task.task_type).upper().strip()
            params = dict(task.parameters or {})
            duration = max(0.0, float(task.duration or params.get("duration", 0.0)))

            if task_type in {"HOLD", "WAIT", "DELAY"}:
                print(f"[MISSION TASK] WP{waypoint_index}: {task_type} START {duration:.1f}s")
                if duration <= 0:
                    return self._finish(task, waypoint_index, sim_time, "HOLD")
                return self._running(task, waypoint_index, sim_time, duration)

            if task_type in {"PHOTO", "CAMERA_CAPTURE", "IMAGE_CAPTURE"}:
                camera = getattr(self.drone, "camera", None)
                if camera is not None:
                    result = camera.capture(sim_time=sim_time, metadata=params)
                    result.update({"task": "PHOTO", "status": "DONE", "waypoint": int(waypoint_index)})
                else:
                    self._capture_index += 1
                    result = {
                        "task": "PHOTO", "status": "DONE",
                        "image_id": f"SIM_IMG_{self._capture_index:05d}",
                        "waypoint": int(waypoint_index), "sim_time": float(sim_time),
                        "metadata": params,
                    }
                return self._record(result, task)

            if task_type == "PHOTO_STOP":
                camera = getattr(self.drone, "camera", None)
                if camera:
                    camera.stop_recording()
                return self._finish(task, waypoint_index, sim_time, "PHOTO_STOP")

            if task_type in {"PHOTO_START", "RECORD_START"}:
                camera = getattr(self.drone, "camera", None)
                if camera:
                    camera.start_recording()
                return self._finish(task, waypoint_index, sim_time, "PHOTO_START")

            if task_type in {"CAMERA_TRIGGER_DISTANCE", "CAM_TRIGGER"}:
                camera = getattr(self.drone, "camera", None)
                distance = float(params.get("trigger_distance_m", params.get("distance", 0.0)))
                if camera:
                    camera.set_trigger_distance(distance)
                return self._finish(task, waypoint_index, sim_time, "CAMERA_TRIGGER_DISTANCE", {"distance_m": distance})

            if task_type in {"GIMBAL", "GIMBAL_PITCHYAW"}:
                pitch = float(params.get("pitch", 0.0))
                yaw = float(params.get("yaw", 0.0))
                if self.drone is not None and hasattr(self.drone, "gimbal_pitch"):
                    self.drone.gimbal_pitch = pitch
                    self.drone.gimbal_yaw = yaw
                print(f"[GIMBAL] PITCH={pitch:.1f} YAW={yaw:.1f}")
                return self._finish(task, waypoint_index, sim_time, "GIMBAL", {"pitch": pitch, "yaw": yaw})

            if task_type in {"RTL", "RETURN_TO_LAUNCH", "HOME"}:
                if self.drone is None:
                    return self._finish(task, waypoint_index, sim_time, "RTL", {"terminal": True})
                result = self.drone.rtl(from_mission=True)
                if not result:
                    return self._finish(task, waypoint_index, sim_time, "RTL", {"terminal": True, "accepted": False})
                print(f"[MISSION TASK] WP{waypoint_index}: RTL -> START")
                return self._finish(task, waypoint_index, sim_time, "RTL", {
                    "terminal": True,
                    "accepted": True,
                    "home_lat": float(self.drone.home_lat),
                    "home_lon": float(self.drone.home_lon),
                    "home_alt": float(self.drone.home_alt),
                })

            if task_type in {"RELAY", "RELAY_ON", "RELAY_OFF"}:
                relay = int(params.get("relay", 0))
                state = int(params.get("state", 1 if task_type != "RELAY_OFF" else 0))
                if self.drone is not None:
                    relays = getattr(self.drone, "relays", None)
                    if relays is None:
                        relays = {}
                        self.drone.relays = relays
                    relays[relay] = bool(state)
                print(f"[RELAY] channel={relay} state={state}")
                return self._finish(task, waypoint_index, sim_time, "RELAY", {"relay": relay, "state": state})

            if task_type in {"ROI", "SET_ROI"}:
                if self.drone is not None:
                    self.drone.roi = dict(params)
                print(f"[ROI] {params}")
                return self._finish(task, waypoint_index, sim_time, "ROI", params)

            if task_type in {"PAYLOAD_RELEASE", "RELEASE"}:
                return self._finish(task, waypoint_index, sim_time, "PAYLOAD_RELEASE", params)

            if task_type in {"SCAN", "SURVEY", "OBSTACLE_SCAN", "LOG", "MARK"}:
                return self._finish(task, waypoint_index, sim_time, task_type, params)

            return self._finish(task, waypoint_index, sim_time, task_type, params)

        duration = max(0.0, float(task.duration or task.parameters.get("duration", 0.0)))
        if duration > 0.0 and float(sim_time) - float(self._active_started_at) < duration:
            return self._running(task, waypoint_index, sim_time, duration)
        return self._finish(task, waypoint_index, sim_time, str(task.task_type).upper().strip())

    def _running(self, task, waypoint_index, sim_time, duration):
        result = {
            "task": str(task.task_type).upper().strip(), "status": "RUNNING",
            "waypoint": int(waypoint_index), "sim_time": float(sim_time),
            "remaining": max(0.0, duration - (float(sim_time) - float(self._active_started_at))),
        }
        self.last_result = result
        return result

    def _finish(self, task, waypoint_index, sim_time, task_name, extra=None):
        result = {"task": task_name, "status": "DONE", "waypoint": int(waypoint_index), "sim_time": float(sim_time)}
        if extra:
            result["metadata"] = dict(extra)
        return self._record(result, task)

    def _record(self, result, task):
        self.last_task = task
        self.last_result = result
        self.history.append(result)
        print(f"[MISSION TASK] WP{result['waypoint']}: {result['task']} -> {result['status']}")
        self._active_task = None
        self._active_started_at = None
        self._active_wp = -1
        return result
