"""MAVLink telemetry sender."""

import time

from pymavlink import mavutil

from .connection import MAVLinkConnection
from .messages import MAVLinkMessages


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
    ) -> bool:

        if not result:

            print(
                f"[TELEMETRY TX FAILED] "
                f"{message_name}"
            )

            return False

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
    # TX STATUS
    # ========================================================

    def print_tx_status(self) -> None:

        print()
        print("======================================")
        print("       MAVLINK TELEMETRY TX")
        print("======================================")

        print(
            f"[TX] Enabled                : "
            f"{self.tx_enabled}"
        )

        print(
            f"[TX] SYSID                  : "
            f"{self.system_id}"
        )

        print(
            f"[TX] COMPID                 : "
            f"{self.component_id}"
        )

        print(
            f"[TX] Total packets          : "
            f"{self.tx_total}"
        )

        print(
            f"[TX] HEARTBEAT              : "
            f"{self.tx_heartbeat}"
        )

        print(
            f"[TX] GLOBAL_POSITION_INT    : "
            f"{self.tx_global_position}"
        )

        print(
            f"[TX] ATTITUDE               : "
            f"{self.tx_attitude}"
        )

        print(
            f"[TX] GPS_RAW_INT            : "
            f"{self.tx_gps}"
        )

        print(
            f"[TX] BATTERY_STATUS         : "
            f"{self.tx_battery}"
        )

        print(
            f"[TX] SYS_STATUS             : "
            f"{self.tx_sys_status}"
        )

        print(
            f"[TX] MISSION_CURRENT       : "
            f"{self.tx_mission_current}"
        )

        print(
            f"[TX] MISSION_ITEM_REACHED  : "
            f"{self.tx_mission_reached}"
        )

        print(
            f"[TX] Last message           : "
            f"{self.last_tx_message}"
        )

        print("======================================")

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

            print(
                f"[HEARTBEAT TX] "
                f"SYSID={self.system_id} "
                f"COMPID={self.component_id}"
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
            )

        except Exception as exc:

            print(
                "[TELEMETRY TX ERROR] "
                f"HEARTBEAT: {exc}"
            )

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
            )

        except Exception as exc:

            print(
                "[TELEMETRY TX ERROR] "
                "GLOBAL_POSITION_INT: "
                f"{exc}"
            )

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

            print(
                "[TELEMETRY ERROR] "
                "GPS conversion: "
                f"{exc}"
            )

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
            )

        except Exception as exc:

            print(
                "[TELEMETRY TX ERROR] "
                "GPS_RAW_INT: "
                f"{exc}"
            )

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
            )

        except Exception as exc:

            print(
                "[TELEMETRY TX ERROR] "
                f"ATTITUDE: {exc}"
            )

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
            )

        except Exception as exc:

            print(
                "[TELEMETRY TX ERROR] "
                f"BATTERY_STATUS: {exc}"
            )

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
            )

        except Exception as exc:

            print(
                "[TELEMETRY TX ERROR] "
                f"SYS_STATUS: {exc}"
            )

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

            print(
                "[MISSION TELEMETRY ERROR] "
                f"{exc}"
            )

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

                print(
                    "[MISSION TX] "
                    f"MISSION_CURRENT "
                    f"seq={sequence}"
                )

            return success

        except Exception as exc:

            print(
                "[MISSION TX ERROR] "
                "MISSION_CURRENT: "
                f"{exc}"
            )

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

                print(
                    "[MISSION TX] "
                    f"MISSION_ITEM_REACHED "
                    f"seq={sequence}"
                )

                return True

            self._tx_ok(
                "MISSION_ITEM_REACHED",
                False,
            )

            return False

        except Exception as exc:

            print(
                "[MISSION TX ERROR] "
                "MISSION_ITEM_REACHED: "
                f"{exc}"
            )

            return False

    # ========================================================
    # RESET MISSION STATE
    # ========================================================

    def reset_mission_state(self):

        self.last_mission_status = 0.0

        self.last_mission_seq = None

        self.mission_reached_seq.clear()

        print(
            "[MISSION TELEMETRY] "
            "Mission state reset"
        )