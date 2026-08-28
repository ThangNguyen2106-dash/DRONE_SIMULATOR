# Mission Write -> Flight Simulation

## MAVLink flow

The simulator implements the standard mission upload handshake:

1. GCS/App sends `MISSION_COUNT`.
2. Simulator sends `MISSION_REQUEST_INT(seq=0)`.
3. GCS/App sends `MISSION_ITEM_INT(seq=0)`.
4. Simulator stores the item and requests the next sequence.
5. Repeat until all items are received.
6. Simulator sends `MISSION_ACK(MAV_MISSION_ACCEPTED)`.
7. The uploaded mission replaces the active mission atomically.

Supported navigation commands:
- `MAV_CMD_NAV_WAYPOINT`
- `MAV_CMD_NAV_TAKEOFF`
- `MAV_CMD_NAV_LAND`
- `MAV_CMD_NAV_LOITER_TIME`

`MAV_CMD_DO_CHANGE_SPEED` is accepted and applies its `param2` speed to following waypoints.

## Mission execution

After upload:

- Select `AUTO` / `MISSION`.
- ARM the simulator.
- If a mission is already uploaded, it starts automatically.
- If the simulator is already armed and in `AUTO` when the upload finishes, the new mission starts automatically.
- The simulator follows latitude, longitude, altitude, waypoint speed, acceptance radius and hold time.
- `LAND` is treated specially: it does not finish the mission at the normal 1 m altitude tolerance; the simulator continues down to ground before completing.
- The simulator publishes `MISSION_CURRENT` and `MISSION_ITEM_REACHED`.

## Recommended app behavior

For a normal mapping mission, send:

`TAKEOFF -> WAYPOINT -> WAYPOINT -> ... -> LAND`

Use `MAV_FRAME_GLOBAL_RELATIVE_ALT_INT` for the mission altitude if the altitude in the app is relative to home.

Example waypoint:
- `frame = MAV_FRAME_GLOBAL_RELATIVE_ALT_INT`
- `command = MAV_CMD_NAV_WAYPOINT`
- `param1 = hold time (s)`
- `param2 = acceptance radius (m)`
- `param4 = yaw (deg)`
- `x = latitude * 1e7`
- `y = longitude * 1e7`
- `z = relative altitude (m)`

## Important

The simulator is a flight-model test environment. It does not model real aircraft dynamics, wind, battery sag, GPS error, EKF, obstacle avoidance or failsafe behavior with flight-control fidelity.
