"""
MAVLink telemetry sender.
"""

import time

from pymavlink import mavutil

from .connection import MAVLinkConnection
from .messages import MAVLinkMessages


class MAVLinkTelemetry:

    def __init__(
        self,
        drone,
        connection: MAVLinkConnection,
        system_id: int = 1,
        component_id: int = 1,
    ):

        self.drone = drone
        self.connection = connection

        self.system_id = system_id
        self.component_id = component_id

        self.messages = MAVLinkMessages(
            system_id=system_id,
            component_id=component_id,
        )

        self.last_heartbeat = 0.0
        self.last_position = 0.0
        self.last_attitude = 0.0
        self.last_gps = 0.0
        self.last_battery = 0.0

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self) -> None:

        now = time.monotonic()

        # ----------------------------------------------------
        # HEARTBEAT - 1 Hz
        # ----------------------------------------------------

        if now - self.last_heartbeat >= 1.0:

            self.send_heartbeat()

            self.last_heartbeat = now

        # ----------------------------------------------------
        # POSITION - 10 Hz
        # ----------------------------------------------------

        if now - self.last_position >= 0.1:

            self.send_global_position()

            self.last_position = now

        # ----------------------------------------------------
        # ATTITUDE - 20 Hz
        # ----------------------------------------------------

        if now - self.last_attitude >= 0.05:

            self.send_attitude()

            self.last_attitude = now

        # ----------------------------------------------------
        # GPS - 5 Hz
        # ----------------------------------------------------

        if now - self.last_gps >= 0.2:

            self.send_gps()

            self.last_gps = now

        # ----------------------------------------------------
        # BATTERY - 1 Hz
        # ----------------------------------------------------

        if now - self.last_battery >= 1.0:

            self.send_battery()

            self.last_battery = now

    # ========================================================
    # HEARTBEAT
    # ========================================================

    def send_heartbeat(self):

        result = self.messages.heartbeat(
            armed=self.drone.armed,
            mode=self.drone.mode.value,
        )

        if self.connection.connection is None:
            return

        self.connection.connection.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_QUADROTOR,
            mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            result["base_mode"],
            result["custom_mode"],
            result["system_status"],
        )

    # ========================================================
    # GLOBAL POSITION
    # ========================================================

    def send_global_position(self):

        if self.connection.connection is None:
            return

        state = self.drone.state

        (
            lat,
            lon,
            alt_mm,
            relative_alt_mm,
            vx,
            vy,
            vz,
            hdg,
        ) = self.messages.global_position_int(
            state
        )

        time_boot_ms = int(
            self.drone.state.sim_time
            * 1000
        ) if hasattr(
            self.drone.state,
            "sim_time",
        ) else int(
            time.monotonic() * 1000
        )

        self.connection.connection.mav.global_position_int_send(
            time_boot_ms,
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
    # GPS
    # ========================================================

    def send_gps(self):

        if self.connection.connection is None:
            return

        state = self.drone.state

        (
        lat,
        lon,
        alt_mm,
        speed_cm_s,
        cog,
    ) = self.messages.gps_raw_int(state)

    # GPS accuracy estimates.
        eph = 100
        epv = 100

    # Number of visible satellites.
        satellites_visible = 12

        self.connection.connection.mav.gps_raw_int_send(
        int(time.monotonic() * 1_000_000),  # time_usec
        3,                                  # fix_type
        lat,                                # latitude * 1e7
        lon,                                # longitude * 1e7
        alt_mm,                             # altitude mm
        eph,                                # horizontal accuracy cm
        epv,                                # vertical accuracy cm
        speed_cm_s,                         # ground speed cm/s
        cog,                                # course over ground cdeg
        satellites_visible,                 # satellites
    )

    # ========================================================
    # ATTITUDE
    # ========================================================

    def send_attitude(self):

        if self.connection.connection is None:
            return

        state = self.drone.state

        (
            roll,
            pitch,
            yaw,
            rollspeed,
            pitchspeed,
            yawspeed,
        ) = self.messages.attitude(
            state
        )

        self.connection.connection.mav.attitude_send(
            int(time.monotonic() * 1000),
            roll,
            pitch,
            yaw,
            rollspeed,
            pitchspeed,
            yawspeed,
        )

    # ========================================================
    # BATTERY
    # ========================================================

    def send_battery(self):

        if self.connection.connection is None:
            return

        battery = max(
            0.0,
            min(
            100.0,
            float(self.drone.state.battery)
            )
    )

    # Battery voltage: 16.0 V
        voltage_mv = 16000

    # Current in 10 mA units.
    # -1 means unknown.
        current_cA = -1

    # Battery remaining percentage.
        remaining = int(battery)

        self.connection.connection.mav.battery_status_send(
        0,  # id
        mavutil.mavlink.MAV_BATTERY_FUNCTION_ALL,
        mavutil.mavlink.MAV_BATTERY_TYPE_LIPO,
        0,  # temperature (cdegC), unknown
        [voltage_mv] + [0] * 9,
        current_cA,
        -1,  # current_consumed
        -1,  # energy_consumed
        remaining,
        0,   # time_remaining
    )