"""
MAVLink message factory.

Creates MAVLink messages from DroneState.
"""

import math

from pymavlink import mavutil


class MAVLinkMessages:

    def __init__(
        self,
        system_id: int = 1,
        component_id: int = 1,
    ):

        self.system_id = system_id
        self.component_id = component_id

    # ========================================================
    # HEARTBEAT
    # ========================================================

    @staticmethod
    def heartbeat(
        armed: bool,
        mode: str,
    ):

        custom_mode = 0

        base_mode = (
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        )

        if armed:

            base_mode |= (
                mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            )

        return {
            "base_mode": base_mode,
            "custom_mode": custom_mode,
            "system_status": (
                mavutil.mavlink.MAV_STATE_ACTIVE
                if armed
                else mavutil.mavlink.MAV_STATE_STANDBY
            ),
        }

    # ========================================================
    # GPS_RAW_INT
    # ========================================================

    def gps_raw_int(
        self,
        state,
    ):

        lat = int(
            state.lat * 1e7
        )

        lon = int(
            state.lon * 1e7
        )

        alt_mm = int(
            state.alt * 1000
        )

        speed_cm_s = int(
            state.ground_speed * 100
        )

        cog = int(
            (state.yaw % 360.0)
            * 100
        )

        return (
            lat,
            lon,
            alt_mm,
            speed_cm_s,
            cog,
        )

    # ========================================================
    # GLOBAL_POSITION_INT
    # ========================================================

    def global_position_int(
        self,
        state,
    ):

        lat = int(
            state.lat * 1e7
        )

        lon = int(
            state.lon * 1e7
        )

        alt_mm = int(
            state.alt * 1000
        )

        relative_alt_mm = int(
            (
                state.alt
                - getattr(
                    state,
                    "home_alt",
                    0.0,
                )
            )
            * 1000
        )

        vx = int(
            math.cos(
                math.radians(
                    state.yaw
                )
            )
            * state.ground_speed
            * 100
        )

        vy = int(
            math.sin(
                math.radians(
                    state.yaw
                )
            )
            * state.ground_speed
            * 100
        )

        vz = int(
            -state.vertical_speed
            * 100
        )

        hdg = int(
            (state.yaw % 360.0)
            * 100
        )

        return (
            lat,
            lon,
            alt_mm,
            relative_alt_mm,
            vx,
            vy,
            vz,
            hdg,
        )

    # ========================================================
    # ATTITUDE
    # ========================================================

    @staticmethod
    def attitude(state):

        roll = math.radians(
            state.roll
        )

        pitch = math.radians(
            state.pitch
        )

        yaw = math.radians(
            state.yaw
        )

        rollspeed = 0.0
        pitchspeed = 0.0
        yawspeed = 0.0

        return (
            roll,
            pitch,
            yaw,
            rollspeed,
            pitchspeed,
            yawspeed,
        )