# Mission Actions V02

Mission upload is interpreted as a sequence of MAVLink mission items. Navigation items move the drone; DO/condition-style commands are attached to the preceding navigation item and are executed after the waypoint is reached.

## Supported mission actions

- `MAV_CMD_NAV_WAYPOINT` — fly to waypoint, including waypoint hold time (`param1`).
- `MAV_CMD_NAV_LOITER_TIME` — fly to the item position and hold for `param1` seconds.
- `MAV_CMD_NAV_TAKEOFF` — mission navigation item for takeoff altitude.
- `MAV_CMD_NAV_LAND` — mission navigation item for landing.
- `MAV_CMD_NAV_RETURN_TO_LAUNCH` — terminal mission action; after the preceding waypoint is reached, RTL starts and the flight controller takes over the return-to-home navigation.
- `MAV_CMD_NAV_DELAY` — translated to a timed HOLD task.
- `MAV_CMD_DO_CHANGE_SPEED` — changes the mission speed used by subsequent navigation items.
- `MAV_CMD_IMAGE_START_CAPTURE` — capture photo at the waypoint.
- `MAV_CMD_IMAGE_STOP_CAPTURE` — stop camera recording.
- `MAV_CMD_DO_SET_CAM_TRIGG_DIST` — enable distance-based camera triggering.
- `MAV_CMD_DO_GIMBAL_MANAGER_PITCHYAW` — set simulated gimbal pitch/yaw.
- `MAV_CMD_DO_SET_SERVO` — simulated payload/servo release.
- `MAV_CMD_DO_SET_RELAY` — simulated relay state.
- `MAV_CMD_DO_SET_ROI` — store the current ROI target for the simulated payload/camera.

## Example: last WP then RTL

Mission Planner/QGroundControl can send:

```text
WP1
WP2
MAV_CMD_NAV_RETURN_TO_LAUNCH
```

The simulator attaches the RTL command to `WP2` during mission upload. Execution becomes:

```text
WP1 -> WP2 -> WP2 reached -> RTL -> HOME -> descend -> HOLD
```

The RTL action is terminal for the mission executor. It does not clear the home navigation target after starting RTL.

## Example: mapping mission

```text
TAKEOFF 30m
WP1 + HOLD 10s + PHOTO
WP2 + GIMBAL DOWN + PHOTO
WP3 + CAMERA TRIGGER EVERY 5m
WP4
RTL
```

The camera simulator writes images and metadata under `simulation_data/photos/`.
