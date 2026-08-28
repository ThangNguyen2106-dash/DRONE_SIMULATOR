"""MAVLink telemetry sender."""

import time

from pymavlink import mavutil

from .connection import MAVLinkConnection
from .messages import MAVLinkMessages
from .mav_logger import mav_log, TX, MISSION


class MAVLinkTelemetry:
    """
    Convert simulated DroneState into MAVLink telemetry.

    This class is TX-only. Incoming MAVLink messages are handled
    by receiver / command / mission receiver modules.

    Default vehicle identity:
        System ID    = 1
        Component ID = 1
    """

    def __init__(
        self,
        drone,
        connection: MAVLinkConnection,
        system_id: int = 1,
        component_id: int = 1,
    ):

        self.drone = drone

        self.connection = connection

        self.system_id = int(system_id)

        self.component_id = int(component_id)

        self.messages = MAVLinkMessages(
            system_id=self.system_id,
            component_id=self.component_id,
        )

        # ====================================================
        # TELEMETRY TIMERS
        # ====================================================

        self.last_heartbeat = 0.0
        self.last_position = 0.0
        self.last_attitude = 0.0
        self.last_gps = 0.0
        self.last_battery = 0.0
        self.last_sys_status = 0.0
        self.last_mission_status = 0.0

        # ====================================================
        # MISSION TRACKING
        # ====================================================

        # Internal mission index:
        #
        # WP1 -> MAVLink seq 0
        # WP2 -> MAVLink seq 1
        # WP3 -> MAVLink seq 2
        #
        self.last_mission_seq = None

        self.mission_reached_seq = set()

        # ====================================================
        # TX DEBUG
        # ====================================================

        self.tx_enabled = True

        # When True, every successfully sent message prints
        # its actual field values (lat/lon/alt, roll/pitch/yaw,
        # battery, ...) instead of just being counted. Off by
        # default since it is high-volume; toggle at runtime
        # with set_debug_verbose().
        self.debug_verbose = False

        self.tx_total = 0

        self.tx_heartbeat = 0
        self.tx_global_position = 0
        self.tx_attitude = 0
        self.tx_gps = 0
        self.tx_battery = 0
        self.tx_sys_status = 0
        self.tx_mission_current = 0
        self.tx_mission_reached = 0

        self.last_tx_message = None
        self.last_tx_time = 0.0

        self.last_tx_debug = 0.0
        self.tx_debug_interval = 1.0

    # ========================================================
    # CONNECTION
    # ========================================================

    def _is_connected(self) -> bool:

        try:
            return (
                self.connection is not None
                and self.connection.is_connected()
            )

        except Exception:
            return False

    # ========================================================
    # STATE
    # ========================================================

    def _state(self):

        if self.drone is None:
            return None

        return self.drone.state

    # ========================================================
    # TIME
    # ========================================================

    def _time_boot_ms(self) -> int:

        state = self._state()

        if state is None:
            return 0

        try:

            sim_time = float(
                getattr(
                    state,
                    "sim_time",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            sim_time = 0.0

        return max(
            0,
            int(
                sim_time * 1000.0
            ),
        )

    # ========================================================

    def _time_usec(self) -> int:

        state = self._state()

        if state is None:
            return 0

        try:

            sim_time = float(
                getattr(
                    state,
                    "sim_time",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            sim_time = 0.0

        return max(
            0,
            int(
                sim_time * 1_000_000.0
            ),
        )

    # ========================================================
    # TX RESULT
    # ========================================================

    def _tx_ok(
        self,
        message_name: str,
        result: bool,
        details: str = "",
    ) -> bool:

        if not result:

            mav_log.warn(TX, f"send failed: {message_name}")

            return False

        if self.debug_verbose and details:

            mav_log.debug(TX, f"{message_name:<20} {details}")

        self.tx_total += 1

        self.last_tx_message = (
            message_name
        )

        self.last_tx_time = (
            time.monotonic()
        )

        if message_name == "HEARTBEAT":

            self.tx_heartbeat += 1

        elif message_name == "GLOBAL_POSITION_INT":

            self.tx_global_position += 1

        elif message_name == "ATTITUDE":

            self.tx_attitude += 1

        elif message_name == "GPS_RAW_INT":

            self.tx_gps += 1

        elif message_name == "BATTERY_STATUS":

            self.tx_battery += 1

        elif message_name == "SYS_STATUS":

            self.tx_sys_status += 1

        elif message_name == "MISSION_CURRENT":

            self.tx_mission_current += 1

        elif message_name == "MISSION_ITEM_REACHED":

            self.tx_mission_reached += 1

        return True

    # ========================================================
    # DEBUG VERBOSE
    # ========================================================

    def set_debug_verbose(
        self,
        enabled: bool,
    ) -> None:

        self.debug_verbose = bool(enabled)

        mav_log.info(
            TX,
            f"Verbose TX debug: {'ON' if self.debug_verbose else 'OFF'}",
        )

    # ========================================================
    # TX STATUS
    #
    # One line, DEBUG level, so it stays silent unless a teammate
    # explicitly turns on DEBUG (mav_log.set_level("DEBUG")) to
    # watch per-message TX counters. Previously this printed an
    # unconditional multi-line block every second.
    # ========================================================

    def print_tx_status(self) -> None:

        mav_log.debug(
            TX,
            f"sysid={self.system_id} compid={self.component_id} "
            f"total={self.tx_total} heartbeat={self.tx_heartbeat} "
            f"pos={self.tx_global_position} att={self.tx_attitude} "
            f"gps={self.tx_gps} battery={self.tx_battery} "
            f"sys_status={self.tx_sys_status} "
            f"mission_current={self.tx_mission_current} "
            f"mission_reached={self.tx_mission_reached} "
            f"last={self.last_tx_message}",
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self) -> None:

        if not self._is_connected():
            return

        now = time.monotonic()

        # ====================================================
        # DEBUG
        # ====================================================

        if (
            self.tx_enabled
            and
            now - self.last_tx_debug
            >= self.tx_debug_interval
        ):

            self.print_tx_status()

            self.last_tx_debug = now

        # ====================================================
        # HEARTBEAT - 1 Hz
        # ====================================================

        if (
            now - self.last_heartbeat
            >= 1.0
        ):

            if self.send_heartbeat():

                self.last_heartbeat = now

        # ====================================================
        # POSITION - 10 Hz
        # ====================================================

        if (
            now - self.last_position
            >= 0.1
        ):

            if self.send_global_position():

                self.last_position = now

        # ====================================================
        # ATTITUDE - 20 Hz
        # ====================================================

        if (
            now - self.last_attitude
            >= 0.05
        ):

            if self.send_attitude():

                self.last_attitude = now

        # ====================================================
        # GPS - 5 Hz
        # ====================================================

        if (
            now - self.last_gps
            >= 0.2
        ):

            if self.send_gps():

                self.last_gps = now

        # ====================================================
        # BATTERY - 1 Hz
        # ====================================================

        if (
            now - self.last_battery
            >= 1.0
        ):

            if self.send_battery():

                self.last_battery = now

        # ====================================================
        # SYS STATUS - 1 Hz
        # ====================================================

        if (
            now - self.last_sys_status
            >= 1.0
        ):

            if self.send_sys_status():

                self.last_sys_status = now

        # ====================================================
        # MISSION - 5 Hz
        # ====================================================

        if (
            now - self.last_mission_status
            >= 0.2
        ):

            self.send_mission_status()

            self.last_mission_status = now

    # ========================================================
    # HEARTBEAT
    # ========================================================

    def send_heartbeat(self) -> bool:

        if not self._is_connected():
            return False

        state = self._state()

        if state is None:
            return False

        mode = getattr(
            state,
            "mode",
            "STANDBY",
        )

        mode = getattr(
            mode,
            "value",
            mode,
        )

        armed = bool(
            getattr(
                state,
                "armed",
                False,
            )
        )

        result = self.messages.heartbeat(
            armed=armed,
            mode=str(mode),
        )

        try:

            mav_log.debug(
                "HEARTBEAT",
                f"sysid={self.system_id} compid={self.component_id}",
            )

            message = (
                self.connection.mavlink
                .heartbeat_encode(
                    mavutil.mavlink.MAV_TYPE_QUADROTOR,
                    mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                    int(result["base_mode"]),
                    int(result["custom_mode"]),
                    int(result["system_status"]),
                )
            )

            result = self.connection.send(
                message
            )

            return self._tx_ok(
                "HEARTBEAT",
                result,
                details=(
                    f"mode={mode} "
                    f"armed={armed}"
                ),
            )

        except Exception as exc:

            mav_log.error(TX, f"HEARTBEAT: {exc}")

            return False

    # ========================================================
    # GLOBAL POSITION
    # ========================================================

    def send_global_position(self) -> bool:

        if not self._is_connected():
            return False

        state = self._state()

        if state is None:
            return False

        try:

            values = (
                self.messages.global_position_int(
                    state
                )
            )

            message = (
                self.connection.mavlink
                .global_position_int_encode(
                    self._time_boot_ms(),
                    *values,
                )
            )

            result = self.connection.send(
                message
            )

            return self._tx_ok(
                "GLOBAL_POSITION_INT",
                result,
                details=(
                    f"lat={state.lat:.7f} "
                    f"lon={state.lon:.7f} "
                    f"alt={state.alt:.2f}m "
                    f"hdg={state.heading:.1f}deg "
                    f"vspd={state.vertical_speed:+.2f}m/s"
                ),
            )

        except Exception as exc:

            mav_log.error(TX, f"GLOBAL_POSITION_INT: {exc}")

            return False

    # ========================================================
    # GPS
    # ========================================================

    def send_gps(self) -> bool:

        if not self._is_connected():
            return False

        state = self._state()

        if state is None:
            return False

        try:

            (
                lat,
                lon,
                alt_mm,
                speed_cm_s,
                cog,
            ) = self.messages.gps_raw_int(
                state
            )

        except Exception as exc:

            mav_log.error(TX, f"GPS conversion: {exc}")

            return False

        # ----------------------------------------------------
        # HDOP
        # ----------------------------------------------------

        try:

            hdop = float(
                getattr(
                    state,
                    "gps_hdop",
                    1.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            hdop = 1.0

        # ----------------------------------------------------
        # VDOP
        # ----------------------------------------------------

        try:

            vdop = float(
                getattr(
                    state,
                    "gps_vdop",
                    1.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            vdop = 1.0

        eph = max(
            0,
            min(
                65535,
                int(
                    hdop * 100.0
                ),
            ),
        )

        epv = max(
            0,
            min(
                65535,
                int(
                    vdop * 100.0
                ),
            ),
        )

        # ----------------------------------------------------
        # GPS FIX
        # ----------------------------------------------------

        try:

            fix_type = int(
                getattr(
                    state,
                    "gps_fix",
                    3,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            fix_type = 3

        fix_type = max(
            0,
            min(
                6,
                fix_type,
            ),
        )

        # ----------------------------------------------------
        # SATELLITES
        # ----------------------------------------------------

        try:

            satellites = int(
                getattr(
                    state,
                    "satellites",
                    12,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            satellites = 12

        satellites = max(
            0,
            min(
                255,
                satellites,
            ),
        )

        try:

            message = (
                self.connection.mavlink
                .gps_raw_int_encode(
                    self._time_usec(),
                    fix_type,
                    int(lat),
                    int(lon),
                    int(alt_mm),
                    eph,
                    epv,
                    int(speed_cm_s),
                    int(cog),
                    satellites,
                )
            )

            result = self.connection.send(
                message
            )

            return self._tx_ok(
                "GPS_RAW_INT",
                result,
                details=(
                    f"fix={fix_type} "
                    f"sats={satellites} "
                    f"eph={eph} epv={epv} "
                    f"spd={speed_cm_s / 100.0:.1f}m/s "
                    f"cog={cog / 100.0:.1f}deg"
                ),
            )

        except Exception as exc:

            mav_log.error(TX, f"GPS_RAW_INT: {exc}")

            return False

    # ========================================================
    # ATTITUDE
    # ========================================================

    def send_attitude(self) -> bool:

        if not self._is_connected():
            return False

        state = self._state()

        if state is None:
            return False

        try:

            values = (
                self.messages.attitude(
                    state
                )
            )

            message = (
                self.connection.mavlink
                .attitude_encode(
                    self._time_boot_ms(),
                    *values,
                )
            )

            result = self.connection.send(
                message
            )

            return self._tx_ok(
                "ATTITUDE",
                result,
                details=(
                    f"roll={state.roll:+.1f}deg "
                    f"pitch={state.pitch:+.1f}deg "
                    f"yaw={state.yaw:.1f}deg "
                    f"gspd={state.ground_speed:.1f}m/s"
                ),
            )

        except Exception as exc:

            mav_log.error(TX, f"ATTITUDE: {exc}")

            return False

    # ========================================================
    # BATTERY
    # ========================================================

    def send_battery(self) -> bool:

        if not self._is_connected():
            return False

        state = self._state()

        if state is None:
            return False

        try:

            battery = float(
                getattr(
                    state,
                    "battery",
                    100.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            battery = 100.0

        battery = max(
            0.0,
            min(
                100.0,
                battery,
            ),
        )

        remaining = int(
            round(battery)
        )

        # ----------------------------------------------------
        # Voltage
        # ----------------------------------------------------

        try:

            voltage = float(
                getattr(
                    state,
                    "voltage",
                    16.8,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            voltage = 16.8

        voltage_mv = max(
            0,
            min(
                65535,
                int(
                    max(
                        0.0,
                        voltage,
                    )
                    * 1000.0
                ),
            ),
        )

        # ----------------------------------------------------
        # Current
        # ----------------------------------------------------

        try:

            current = float(
                getattr(
                    state,
                    "current",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            current = 0.0

        if current < 0.0:

            current_cA = -1

        else:

            current_cA = max(
                0,
                min(
                    32767,
                    int(
                        current * 100.0
                    ),
                ),
            )

        # ----------------------------------------------------
        # 4S battery
        # ----------------------------------------------------

        cell_count = 4

        cell_voltage = int(
            voltage_mv
            / cell_count
        )

        voltages = (
            [cell_voltage] * cell_count
        )

        voltages.extend(
            [0] * (
                10 - len(voltages)
            )
        )

        try:

            message = (
                self.connection.mavlink
                .battery_status_encode(
                    0,
                    mavutil.mavlink.MAV_BATTERY_FUNCTION_ALL,
                    mavutil.mavlink.MAV_BATTERY_TYPE_LIPO,
                    0,
                    voltages,
                    current_cA,
                    -1,
                    -1,
                    remaining,
                )
            )

            result = self.connection.send(
                message
            )

            return self._tx_ok(
                "BATTERY_STATUS",
                result,
                details=(
                    f"remaining={remaining}% "
                    f"voltage={voltage_mv / 1000.0:.2f}V "
                    f"current={current:.2f}A"
                ),
            )

        except Exception as exc:

            mav_log.error(TX, f"BATTERY_STATUS: {exc}")

            return False

    # ========================================================
    # SYS STATUS
    # ========================================================

    def send_sys_status(self) -> bool:

        if not self._is_connected():
            return False

        state = self._state()

        if state is None:
            return False

        # ----------------------------------------------------
        # Battery
        # ----------------------------------------------------

        try:

            battery = float(
                getattr(
                    state,
                    "battery",
                    100.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            battery = 100.0

        battery = max(
            0.0,
            min(
                100.0,
                battery,
            ),
        )

        battery_remaining = int(
            round(battery)
        )

        # ----------------------------------------------------
        # Voltage
        # ----------------------------------------------------

        try:

            voltage = float(
                getattr(
                    state,
                    "voltage",
                    16.8,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            voltage = 16.8

        voltage_mv = max(
            0,
            min(
                65535,
                int(
                    max(
                        0.0,
                        voltage,
                    )
                    * 1000.0
                ),
            ),
        )

        # ----------------------------------------------------
        # Current
        # ----------------------------------------------------

        try:

            current = float(
                getattr(
                    state,
                    "current",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            current = 0.0

        if current < 0.0:

            current_cA = -1

        else:

            current_cA = max(
                0,
                min(
                    32767,
                    int(
                        current * 100.0
                    ),
                ),
            )

        # ----------------------------------------------------
        # Sensors
        # ----------------------------------------------------

        onboard_sensors = (
            mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_GYRO
            |
            mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_ACCEL
            |
            mavutil.mavlink.MAV_SYS_STATUS_SENSOR_3D_MAG
            |
            mavutil.mavlink.MAV_SYS_STATUS_SENSOR_GPS
        )

        try:

            message = (
                self.connection.mavlink
                .sys_status_encode(
                    onboard_sensors,
                    onboard_sensors,
                    onboard_sensors,
                    0,
                    voltage_mv,
                    current_cA,
                    battery_remaining,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                )
            )

            result = self.connection.send(
                message
            )

            return self._tx_ok(
                "SYS_STATUS",
                result,
                details=(
                    f"voltage={voltage_mv / 1000.0:.2f}V "
                    f"battery={battery_remaining}%"
                ),
            )

        except Exception as exc:

            mav_log.error(TX, f"SYS_STATUS: {exc}")

            return False

    # ========================================================
    # MISSION STATUS
    # ========================================================

    def send_mission_status(self) -> None:
        """
        Send MAVLink mission progress.

        MISSION_CURRENT:
            Current active MAVLink mission sequence.

        MISSION_ITEM_REACHED:
            Waypoint sequence that was reached.
        """

        if not self._is_connected():
            return

        if self.drone is None:
            return

        try:

            status = (
                self.drone.get_status()
            )

        except Exception as exc:

            mav_log.error(MISSION, f"{exc}")

            return

        mission_count = int(
            status.get(
                "mission_count",
                0,
            )
        )

        mission_active = bool(
            status.get(
                "mission_active",
                False,
            )
        )

        mission_completed = bool(
            status.get(
                "mission_completed",
                False,
            )
        )

        current_waypoint = status.get(
            "current_waypoint",
            None,
        )

        # ====================================================
        # NO MISSION
        # ====================================================

        if mission_count <= 0:

            self.last_mission_seq = None

            self.mission_reached_seq.clear()

            return

        # ====================================================
        # CONVERT WP → MAVLINK SEQ
        # ====================================================

        if current_waypoint is None:

            current_seq = None

        else:

            try:
                wp_obj = self.drone.mission.get_waypoint(
                    int(current_waypoint)
                )
                current_seq = int(
                    getattr(wp_obj, "source_seq", int(current_waypoint) - 1)
                )
            except Exception:
                current_seq = None

        # ====================================================
        # CURRENT WP
        # ====================================================

        if (
            mission_active
            and
            current_seq is not None
        ):

            self._send_mission_current(
                current_seq
            )

        # ====================================================
        # WP CHANGE
        # ====================================================

        if (
            self.last_mission_seq is not None
            and
            current_seq is not None
            and
            current_seq
            != self.last_mission_seq
        ):

            previous_seq = (
                self.last_mission_seq
            )

            self._send_mission_item_reached(
                previous_seq
            )

        # ====================================================
        # MISSION COMPLETE
        # ====================================================

        if mission_completed:

            if current_seq is not None:

                self._send_mission_item_reached(
                    current_seq
                )

        # ====================================================
        # SAVE CURRENT SEQ
        # ====================================================

        if current_seq is not None:

            self.last_mission_seq = (
                current_seq
            )

    # ========================================================
    # MISSION CURRENT
    # ========================================================

    def _send_mission_current(
        self,
        sequence: int,
    ) -> bool:

        try:

            message = (
                self.connection.mavlink
                .mission_current_encode(
                    int(sequence)
                )
            )

            result = self.connection.send(
                message
            )

            success = self._tx_ok(
                "MISSION_CURRENT",
                result,
            )

            if (
                success
                and
                self.last_mission_seq
                != sequence
            ):

                mav_log.info(MISSION, f"MISSION_CURRENT seq={sequence}")

            return success

        except Exception as exc:

            mav_log.error(MISSION, f"MISSION_CURRENT: {exc}")

            return False

    # ========================================================
    # MISSION ITEM REACHED
    # ========================================================

    def _send_mission_item_reached(
        self,
        sequence: int,
    ) -> bool:

        sequence = int(
            sequence
        )

        if sequence in (
            self.mission_reached_seq
        ):

            return True

        try:

            message = (
                self.connection.mavlink
                .mission_item_reached_encode(
                    sequence
                )
            )

            result = self.connection.send(
                message
            )

            if result:

                self.mission_reached_seq.add(
                    sequence
                )

                self._tx_ok(
                    "MISSION_ITEM_REACHED",
                    True,
                )

                mav_log.info(MISSION, f"MISSION_ITEM_REACHED seq={sequence}")

                return True

            self._tx_ok(
                "MISSION_ITEM_REACHED",
                False,
            )

            return False

        except Exception as exc:

            mav_log.error(MISSION, f"MISSION_ITEM_REACHED: {exc}")

            return False

    # ========================================================
    # RESET MISSION STATE
    # ========================================================

    def reset_mission_state(self):

        self.last_mission_status = 0.0

        self.last_mission_seq = None

        self.mission_reached_seq.clear()

        mav_log.info(MISSION, "Mission state reset")