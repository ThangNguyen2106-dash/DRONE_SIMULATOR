import time
import traceback

from PySide6.QtCore import (
    QThread,
    Signal,
)

from simulator.drone import Drone
from simulator.flight_controller import FlightController

from mavlink.connection import MAVLinkConnection
from mavlink.telemetry import MAVLinkTelemetry
from mavlink.mission_receiver import MissionReceiver
from mavlink.command_receiver import CommandReceiver


class SimulationWorker(QThread):

    # ========================================================
    # SIGNALS
    # ========================================================

    telemetry_updated = Signal(dict)

    status_changed = Signal(str)

    error_occurred = Signal(str)

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        drone_config=None,
        mavlink_config=None,
        parent=None,
    ):

        super().__init__(parent)

        self.drone_config = (
            drone_config or {}
        )

        self.mavlink_config = (
            mavlink_config or {}
        )

        # ====================================================
        # RUNTIME COMMAND QUEUE
        # ====================================================

        self.command_queue = []

        # ====================================================
        # STATE
        # ====================================================

        self.running = False

        self.drone = None

        self.controller = None

        self.mavlink = None

        self.telemetry = None

        self.mission_receiver = None

        self.command_receiver = None

        # ====================================================
        # INITIAL RUNTIME VALUES
        # ====================================================

        self.runtime_mode = None

        self.runtime_altitude = None

        self.runtime_speed = None

        self.runtime_heading = None

        self.runtime_latitude = None

        self.runtime_longitude = None

        self.runtime_roll = None

        self.runtime_pitch = None

        self.runtime_yaw = None

        self.runtime_battery = None

    # ========================================================
    # QUEUE RUNTIME COMMAND
    # ========================================================

    def queue_command(
        self,
        command,
        value=None,
    ):
        """
        Add a runtime command.

        This method can be called by the GUI thread.

        The actual Drone modification happens inside
        SimulationWorker.run(), therefore all simulation
        objects remain owned by the simulation thread.
        """

        self.command_queue.append(
            (
                command,
                value,
            )
        )

    # ========================================================
    # PROCESS RUNTIME COMMANDS
    # ========================================================

    def _process_runtime_commands(self):

        while self.command_queue:

            command, value = (
                self.command_queue.pop(0)
            )

            try:

                self._execute_runtime_command(
                    command,
                    value,
                )

            except Exception as exc:

                print(
                    "[RUNTIME COMMAND ERROR] "
                    f"{command}: "
                    f"{type(exc).__name__}: {exc}"
                )

    # ========================================================
    # EXECUTE RUNTIME COMMAND
    # ========================================================

    def _execute_runtime_command(
        self,
        command,
        value,
    ):

        if self.drone is None:

            return

        # ====================================================
        # MODE
        # ====================================================

        if command == "mode":

            result = (
                self.drone.set_mode(
                    value
                )
            )

            if result:

                self.runtime_mode = (
                    self.drone.get_mode()
                )

                print(
                    f"[RUNTIME] MODE "
                    f"-> {self.runtime_mode}"
                )

            else:

                print(
                    f"[RUNTIME] MODE FAILED "
                    f"-> {value}"
                )

            return

        # ====================================================
        # ALTITUDE
        # ====================================================

        if command == "altitude":

            result = (
                self.drone.set_altitude(
                    value
                )
            )

            if result:

                self.runtime_altitude = float(
                    value
                )

                print(
                    f"[RUNTIME] ALTITUDE "
                    f"-> {value}"
                )

            return

        # ====================================================
        # ALTITUDE HOLD
        # ====================================================

        if command == "altitude_hold":

            result = (
                self.drone.set_altitude_hold(
                    value
                )
            )

            if result:

                self.runtime_mode = (
                    "ALT_HOLD"
                )

                self.runtime_altitude = float(
                    value
                )

                print(
                    f"[RUNTIME] ALT HOLD "
                    f"-> {value}"
                )

            return

        # ====================================================
        # SPEED
        # ====================================================

        if command == "speed":

            result = (
                self.drone.set_speed(
                    value
                )
            )

            if result:

                self.runtime_speed = float(
                    value
                )

                print(
                    f"[RUNTIME] SPEED "
                    f"-> {value}"
                )

            return

        # ====================================================
        # HEADING
        # ====================================================

        if command == "heading":

            result = (
                self.drone.set_heading(
                    value
                )
            )

            if result:

                self.runtime_heading = float(
                    value
                )

                print(
                    f"[RUNTIME] HEADING "
                    f"-> {value}"
                )

            return

        # ====================================================
        # LATITUDE
        # ====================================================

        if command == "latitude":

            result = (
                self.drone.set_latitude(
                    value
                )
            )

            if result:

                self.runtime_latitude = float(
                    value
                )

                print(
                    f"[RUNTIME] LATITUDE "
                    f"-> {value}"
                )

            return

        # ====================================================
        # LONGITUDE
        # ====================================================

        if command == "longitude":

            result = (
                self.drone.set_longitude(
                    value
                )
            )

            if result:

                self.runtime_longitude = float(
                    value
                )

                print(
                    f"[RUNTIME] LONGITUDE "
                    f"-> {value}"
                )

            return

        # ====================================================
        # POSITION
        # ====================================================

        if command == "position":

            latitude = value.get(
                "latitude"
            )

            longitude = value.get(
                "longitude"
            )

            altitude = value.get(
                "altitude",
                None,
            )

            result = (
                self.drone.set_position(
                    lat=latitude,
                    lon=longitude,
                    alt=altitude,
                )
            )

            if result:

                self.runtime_latitude = float(
                    latitude
                )

                self.runtime_longitude = float(
                    longitude
                )

                if altitude is not None:

                    self.runtime_altitude = float(
                        altitude
                    )

                print(
                    "[RUNTIME] POSITION "
                    f"-> "
                    f"{latitude}, "
                    f"{longitude}, "
                    f"{altitude}"
                )

            return

        # ====================================================
        # ROLL
        # ====================================================

        if command == "roll":

            result = (
                self.drone.set_roll(
                    value
                )
            )

            if result:

                self.runtime_roll = float(
                    value
                )

            return

        # ====================================================
        # PITCH
        # ====================================================

        if command == "pitch":

            result = (
                self.drone.set_pitch(
                    value
                )
            )

            if result:

                self.runtime_pitch = float(
                    value
                )

            return

        # ====================================================
        # YAW
        # ====================================================

        if command == "yaw":

            result = (
                self.drone.set_yaw(
                    value
                )
            )

            if result:

                self.runtime_yaw = float(
                    value
                )

            return

        # ====================================================
        # ATTITUDE
        # ====================================================

        if command == "attitude":

            result = (
                self.drone.set_attitude(
                    roll=value.get(
                        "roll"
                    ),
                    pitch=value.get(
                        "pitch"
                    ),
                    yaw=value.get(
                        "yaw"
                    ),
                )
            )

            if result:

                if value.get("roll") is not None:

                    self.runtime_roll = float(
                        value["roll"]
                    )

                if value.get("pitch") is not None:

                    self.runtime_pitch = float(
                        value["pitch"]
                    )

                if value.get("yaw") is not None:

                    self.runtime_yaw = float(
                        value["yaw"]
                    )

            return

        # ====================================================
        # BATTERY
        # ====================================================

        if command == "battery":

            result = (
                self.drone.set_battery(
                    value
                )
            )

            if result:

                self.runtime_battery = float(
                    value
                )

                print(
                    f"[RUNTIME] BATTERY "
                    f"-> {value}%"
                )

            return

        # ====================================================
        # GPS
        # ====================================================

        if command == "gps":

            if not isinstance(
                value,
                dict,
            ):

                return

            result = (
                self.drone.set_gps(
                    fix_type=value.get(
                        "fix_type"
                    ),
                    satellites=value.get(
                        "satellites"
                    ),
                    hdop=value.get(
                        "hdop"
                    ),
                    vdop=value.get(
                        "vdop"
                    ),
                )
            )

            if result:

                print(
                    "[RUNTIME] GPS updated"
                )

            return

        # ====================================================
        # ARM
        # ====================================================

        if command == "arm":

            result = (
                self.drone.arm()
            )

            print(
                f"[RUNTIME] ARM -> {result}"
            )

            return

        # ====================================================
        # DISARM
        # ====================================================

        if command == "disarm":

            result = (
                self.drone.disarm()
            )

            print(
                f"[RUNTIME] DISARM -> {result}"
            )

            return

        # ====================================================
        # TAKEOFF
        # ====================================================

        if command == "takeoff":

            result = (
                self.drone.takeoff(
                    value
                )
            )

            print(
                f"[RUNTIME] TAKEOFF "
                f"{value}m -> {result}"
            )

            return

        # ====================================================
        # LAND
        # ====================================================

        if command == "land":

            result = (
                self.drone.land()
            )

            print(
                f"[RUNTIME] LAND -> {result}"
            )

            return

        # ====================================================
        # RTL
        # ====================================================

        if command == "rtl":

            result = (
                self.drone.rtl()
            )

            print(
                f"[RUNTIME] RTL -> {result}"
            )

            return

        # ====================================================
        # STOP MISSION
        # ====================================================

        if command == "stop_mission":

            result = (
                self.drone.stop_mission()
            )

            print(
                f"[RUNTIME] STOP MISSION "
                f"-> {result}"
            )

            return

        # ====================================================
        # START MISSION
        # ====================================================

        if command == "start_mission":

            result = (
                self.drone.start_mission()
            )

            print(
                f"[RUNTIME] START MISSION "
                f"-> {result}"
            )

            return

        # ====================================================
        # UNKNOWN
        # ====================================================

        print(
            f"[RUNTIME] Unknown command: "
            f"{command}"
        )

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        self.running = True

        try:

            print()
            print("======================================")
            print("SIMULATION WORKER START")
            print("======================================")

            # ==================================================
            # DRONE CONFIG
            # ==================================================

            latitude = float(
                self.drone_config.get(
                    "lat",
                    10.8231000,
                )
            )

            longitude = float(
                self.drone_config.get(
                    "lon",
                    106.6297000,
                )
            )

            altitude = float(
                self.drone_config.get(
                    "alt",
                    0.0,
                )
            )

            print(
                f"[SIM] LAT={latitude}"
            )

            print(
                f"[SIM] LON={longitude}"
            )

            print(
                f"[SIM] ALT={altitude}"
            )

            # ==================================================
            # CREATE DRONE
            # ==================================================

            print(
                "[SIM] Creating Drone..."
            )

            self.drone = Drone(
                lat=latitude,
                lon=longitude,
                alt=altitude,
            )

            print(
                "[SIM] Drone OK"
            )

            # ==================================================
            # CONTROLLER
            # ==================================================

            print(
                "[SIM] Creating FlightController..."
            )

            self.controller = FlightController(
                self.drone
            )

            print(
                "[SIM] FlightController OK"
            )

            # ==================================================
            # MAVLINK CONFIG
            # ==================================================

            connection_string = (
                self.mavlink_config.get(
                    "connection_string",
                    "udp:0.0.0.0:14550",
                )
            )

            system_id = int(
                self.mavlink_config.get(
                    "system_id",
                    1,
                )
            )

            component_id = int(
                self.mavlink_config.get(
                    "component_id",
                    1,
                )
            )

            telemetry_rate = float(
                self.mavlink_config.get(
                    "telemetry_rate",
                    20.0,
                )
            )

            print(
                f"[SIM] MAVLink: "
                f"{connection_string}"
            )

            print(
                f"[SIM] System ID: "
                f"{system_id}"
            )

            print(
                f"[SIM] Component ID: "
                f"{component_id}"
            )

            print(
                f"[SIM] Telemetry Rate: "
                f"{telemetry_rate} Hz"
            )

            # ==================================================
            # MAVLINK
            # ==================================================

            print(
                "[SIM] Creating MAVLink connection..."
            )

            self.mavlink = MAVLinkConnection(
                connection_string=connection_string,
                source_system=system_id,
                source_component=component_id,
            )

            self.mavlink.connect()

            print(
                "[SIM] MAVLink OK"
            )

            # ==================================================
            # MISSION RECEIVER
            # ==================================================

            self.mission_receiver = MissionReceiver(
                connection=self.mavlink,
                mission=self.drone.mission,
                system_id=system_id,
                component_id=component_id,
            )

            print(
                "[SIM] MissionReceiver OK"
            )

            # ==================================================
            # COMMAND RECEIVER
            # ==================================================

            self.command_receiver = CommandReceiver(
                connection=self.mavlink,
                controller=self.controller,
                drone=self.drone,
            )

            print(
                "[SIM] CommandReceiver OK"
            )

            # ==================================================
            # TELEMETRY
            # ==================================================

            self.telemetry = MAVLinkTelemetry(
                drone=self.drone,
                connection=self.mavlink,
                system_id=system_id,
                component_id=component_id,
            )

            print(
                "[SIM] Telemetry OK"
            )

            # ==================================================
            # INITIAL RUNTIME VALUES
            # ==================================================

            self.runtime_mode = (
                self.drone.get_mode()
            )

            self.runtime_altitude = altitude

            self.runtime_speed = 0.0

            self.runtime_heading = float(
                getattr(
                    self.drone.state,
                    "heading",
                    0.0,
                )
            )

            self.runtime_latitude = latitude

            self.runtime_longitude = longitude

            self.runtime_roll = 0.0

            self.runtime_pitch = 0.0

            self.runtime_yaw = 0.0

            self.runtime_battery = 100.0

            # ==================================================
            # READY
            # ==================================================

            print(
                "[SIM] Waiting for GCS..."
            )

            self.status_changed.emit(
                "READY"
            )

            # ==================================================
            # SIMULATION LOOP
            # ==================================================

            last_time = time.monotonic()

            while self.running:

                now = time.monotonic()

                dt = (
                    now - last_time
                )

                last_time = now

                dt = max(
                    0.0,
                    min(
                        dt,
                        0.1,
                    ),
                )

                # ==================================================
                # RUNTIME COMMANDS
                # ==================================================

                self._process_runtime_commands()

                # ==================================================
                # MAVLINK RX
                # ==================================================

                while self.running:

                    message = self.mavlink.receive(
                        blocking=False
                    )

                    if message is None:

                        break

                    message_type = (
                        message.get_type()
                    )

                    print(
                        f"[MAVLINK RX] "
                        f"{message_type}"
                    )

                    # ------------------------------------------------
                    # Mission
                    # ------------------------------------------------

                    if self.mission_receiver is not None:

                        self.mission_receiver.process(
                            message
                        )

                    # ------------------------------------------------
                    # Commands
                    # ------------------------------------------------

                    if self.command_receiver is not None:

                        self.command_receiver.process(
                            message
                        )

                # ==================================================
                # DRONE UPDATE
                # ==================================================

                if self.drone is not None:

                    self.drone.update(
                        dt
                    )

                # ==================================================
                # TELEMETRY
                # ==================================================

                if self.telemetry is not None:

                    self.telemetry.update()

                # ==================================================
                # GUI
                # ==================================================

                if self.drone is not None:

                    status = (
                        self.drone.get_status()
                    )

                    self.telemetry_updated.emit(
                        status
                    )

                # ==================================================
                # LOOP
                # ==================================================

                time.sleep(
                    0.01
                )

        except Exception as exc:

            message = (
                f"{type(exc).__name__}: {exc}"
            )

            print()
            print(
                "======================================"
            )
            print(
                "[SIMULATION ERROR]"
            )
            print(
                message
            )
            print(
                "======================================"
            )

            traceback.print_exc()

            self.error_occurred.emit(
                message
            )

        finally:

            self._cleanup()

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False

    # ========================================================
    # CLEANUP
    # ========================================================

    def _cleanup(self):

        self.running = False

        self.command_queue.clear()

        if self.mavlink is not None:

            try:

                self.mavlink.close()

            except Exception as exc:

                print(
                    f"[MAVLINK CLOSE ERROR] "
                    f"{exc}"
                )

            self.mavlink = None

        self.telemetry = None

        self.command_receiver = None

        self.mission_receiver = None

        self.controller = None

        self.drone = None

        print(
            "[SIM] Worker finished"
        )

        self.status_changed.emit(
            "STOPPED"
        )