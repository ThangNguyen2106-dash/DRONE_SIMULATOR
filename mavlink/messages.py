"""
MAVLink message factory.

Creates MAVLink telemetry values from DroneState.
"""

import math

from pymavlink import mavutil


class MAVLinkMessages:

    def __init__(
        self,
        system_id: int = 1,
        component_id: int = 1,
    ):

        self.system_id = int(system_id)
        self.component_id = int(component_id)

    # ========================================================
    # HEARTBEAT
    # ========================================================

    @staticmethod
    def heartbeat(
        armed: bool,
        mode: str,
    ):
        """
        Convert simulator state into HEARTBEAT fields.
        """

        custom_mode = 0

        base_mode = (
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        )

        if armed:
            base_mode |= (
                mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            )

        return {
            "base_mode": int(base_mode),
            "custom_mode": int(custom_mode),
            "system_status": int(
                mavutil.mavlink.MAV_STATE_ACTIVE
                if armed
                else mavutil.mavlink.MAV_STATE_STANDBY
            ),
        }

    # ========================================================
    # GPS_RAW_INT
    # ========================================================

    @staticmethod
    def gps_raw_int(state):
        """
        Convert DroneState to GPS_RAW_INT fields.

        Returns:

            lat             int   degE7
            lon             int   degE7
            alt             int   mm
            speed           int   cm/s
            cog             int   cdeg
        """

        lat = int(
            float(state.lat) * 1e7
        )

        lon = int(
            float(state.lon) * 1e7
        )

        alt_mm = int(
            float(state.alt) * 1000.0
        )

        ground_speed = float(
            getattr(
                state,
                "ground_speed",
                0.0,
            )
        )

        speed_cm_s = int(
            max(
                0.0,
                ground_speed,
            ) * 100.0
        )

        yaw = float(
            getattr(
                state,
                "yaw",
                0.0,
            )
        )

        cog = int(
            (yaw % 360.0) * 100.0
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

    @staticmethod
    def global_position_int(state):
        """
        Convert DroneState to GLOBAL_POSITION_INT.

        Returns:

            lat
            lon
            alt
            relative_alt
            vx
            vy
            vz
            hdg
        """

        # ----------------------------------------------------
        # POSITION
        # ----------------------------------------------------

        lat = int(
            float(state.lat) * 1e7
        )

        lon = int(
            float(state.lon) * 1e7
        )

        alt = float(
            getattr(
                state,
                "alt",
                0.0,
            )
        )

        alt_mm = int(
            alt * 1000.0
        )

        # ----------------------------------------------------
        # RELATIVE ALTITUDE
        # ----------------------------------------------------

        home_alt = float(
            getattr(
                state,
                "home_alt",
                0.0,
            )
        )

        relative_alt_mm = int(
            (alt - home_alt) * 1000.0
        )

        # ----------------------------------------------------
        # VELOCITY
        # ----------------------------------------------------

        ground_speed = float(
            getattr(
                state,
                "ground_speed",
                0.0,
            )
        )

        yaw = float(
            getattr(
                state,
                "yaw",
                0.0,
            )
        )

        yaw_rad = math.radians(
            yaw
        )

        # North velocity
        vx = int(
            math.cos(yaw_rad)
            * ground_speed
            * 100.0
        )

        # East velocity
        vy = int(
            math.sin(yaw_rad)
            * ground_speed
            * 100.0
        )

        # Down velocity
        vertical_speed = float(
            getattr(
                state,
                "vertical_speed",
                0.0,
            )
        )

        vz = int(
            -vertical_speed
            * 100.0
        )

        # ----------------------------------------------------
        # HEADING
        # ----------------------------------------------------

        hdg = int(
            (yaw % 360.0)
            * 100.0
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
        """
        Convert DroneState to ATTITUDE fields.

        MAVLink expects radians.
        Simulator state uses degrees.
        """

        roll = math.radians(
            float(
                getattr(
                    state,
                    "roll",
                    0.0,
                )
            )
        )

        pitch = math.radians(
            float(
                getattr(
                    state,
                    "pitch",
                    0.0,
                )
            )
        )

        yaw = math.radians(
            float(
                getattr(
                    state,
                    "yaw",
                    0.0,
                )
            )
        )

        rollspeed = float(
            getattr(
                state,
                "roll_speed",
                0.0,
            )
        )

        pitchspeed = float(
            getattr(
                state,
                "pitch_speed",
                0.0,
            )
        )

        yawspeed = float(
            getattr(
                state,
                "yaw_speed",
                0.0,
            )
        )

        return (
            roll,
            pitch,
            yaw,
            rollspeed,
            pitchspeed,
            yawspeed,
        )