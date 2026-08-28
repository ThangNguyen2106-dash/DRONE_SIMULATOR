import time
import traceback
import queue

from PySide6.QtCore import QThread, Signal

from simulator.drone import Drone
from simulator.flight_controller import FlightController

from mavlink.connection import MAVLinkConnection
from mavlink.telemetry import MAVLinkTelemetry
from mavlink.mission_receiver import MissionReceiver
from mavlink.command_receiver import CommandReceiver


class SimulationWorker(QThread):
    """
    Main simulation worker.

    Architecture:

        Drone Simulator
              |
              | MAVLink TX
              v
        Ground Station
              |
              | MAVLink RX
              v
        Drone Simulator

    Runtime control:

        GUI
         |
         | queue_command()
         v
        Thread-safe Queue
         |
         v
        Simulation Thread
         |
         v
        Drone / FlightModel

    Default UDP configuration:

        Simulator TX -> 127.0.0.1:14550
        Simulator RX <- 0.0.0.0:14551
    """

    # ========================================================
    # SIGNALS
    # ========================================================

    telemetry_updated = Signal(dict)

    status_changed = Signal(str)

    error_occurred = Signal(str)

    mission_updated = Signal(dict)

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
            drone_config
            if isinstance(
                drone_config,
                dict,
            )
            else {}
        )

        self.mavlink_config = (
            mavlink_config
            if isinstance(
                mavlink_config,
                dict,
            )
            else {}
        )

        # ====================================================
        # THREAD STATE
        # ====================================================

        self.running = False

        # ====================================================
        # RUNTIME COMMAND QUEUE
        # ====================================================

        self.command_queue = queue.Queue()

        # ====================================================
        # OBJECTS
        # ====================================================

        self.drone = None

        self.controller = None

        self.mavlink = None

        self.telemetry = None

        self.mission_receiver = None

        self.command_receiver = None

        self._last_mission_snapshot = None

        # ====================================================
        # RUNTIME STATUS
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
        Queue a runtime command.

        Safe to call from the GUI thread while the
        simulation is running.
        """

        try:

            self.command_queue.put(
                (
                    command,
                    value,
                )
            )

        except Exception as exc:

            print(
                "[RUNTIME QUEUE ERROR] "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

    # ========================================================
    # PROCESS RUNTIME COMMANDS
    # ========================================================

    def _process_runtime_commands(
        self,
    ):
        """
        Execute all pending runtime commands.

        This function must only be called from the
        simulation thread.
        """

        while self.running:

            try:

                command, value = (
                    self.command_queue.get_nowait()
                )

            except queue.Empty:

                break

            try:

                self._execute_runtime_command(
                    command,
                    value,
                )

            except Exception as exc:

                print(
                    "[RUNTIME COMMAND ERROR] "
                    f"{command}: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

            finally:

                self.command_queue.task_done()

    # ========================================================
    # EXECUTE RUNTIME COMMAND
    # ========================================================

    def _execute_runtime_command(
        self,
        command,
        value,
    ):
        """
        Execute one runtime command.

        All Drone modifications happen inside the
        simulation thread.
        """

        if self.drone is None:

            return

        # ====================================================
        # MODE
        # ====================================================

        if command == "mode":

            result = self.drone.set_mode(
                value
            )

            if result:

                self.runtime_mode = (
                    self.drone.get_mode()
                )

                print(
                    "[RUNTIME] MODE -> "
                    f"{self.runtime_mode}"
                )

            else:

                print(
                    "[RUNTIME] MODE FAILED -> "
                    f"{value}"
                )

            return

        # ====================================================
        # FREE
        # ====================================================

        if command == "free":

            result = (
                self.drone.set_free_flight()
            )

            if result:

                self.runtime_mode = "FREE"

                print(
                    "[RUNTIME] MODE -> FREE"
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

                self.runtime_mode = "ALT_HOLD"

                self.runtime_altitude = (
                    float(value)
                )

                print(
                    "[RUNTIME] ALT HOLD -> "
                    f"{value:.2f} m"
                )

            else:

                print(
                    "[RUNTIME] ALT HOLD FAILED"
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

                self.runtime_altitude = (
                    float(value)
                )

                print(
                    "[RUNTIME] ALTITUDE -> "
                    f"{value:.2f} m"
                )

            else:

                print(
                    "[RUNTIME] ALTITUDE FAILED"
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

                self.runtime_speed = (
                    float(value)
                )

                print(
                    "[RUNTIME] SPEED -> "
                    f"{value:.2f} m/s"
                )

            else:

                print(
                    "[RUNTIME] SPEED FAILED"
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

                self.runtime_heading = (
                    float(value)
                )

                print(
                    "[RUNTIME] HEADING -> "
                    f"{value:.2f} deg"
                )

            else:

                print(
                    "[RUNTIME] HEADING FAILED"
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

                self.runtime_latitude = (
                    float(value)
                )

                print(
                    "[RUNTIME] LATITUDE -> "
                    f"{value:.7f}"
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

                self.runtime_longitude = (
                    float(value)
                )

                print(
                    "[RUNTIME] LONGITUDE -> "
                    f"{value:.7f}"
                )

            return

        # ====================================================
        # POSITION
        # ====================================================

        if command == "position":

            if not isinstance(
                value,
                dict,
            ):

                return

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

                self.runtime_latitude = (
                    float(latitude)
                )

                self.runtime_longitude = (
                    float(longitude)
                )

                if altitude is not None:

                    self.runtime_altitude = (
                        float(altitude)
                    )

                print(
                    "[RUNTIME] POSITION -> "
                    f"LAT={latitude:.7f} "
                    f"LON={longitude:.7f} "
                    f"ALT={altitude}"
                )

            else:

                print(
                    "[RUNTIME] POSITION FAILED"
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

                self.runtime_roll = (
                    float(value)
                )

                print(
                    "[RUNTIME] ROLL -> "
                    f"{value:.2f} deg"
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

                self.runtime_pitch = (
                    float(value)
                )

                print(
                    "[RUNTIME] PITCH -> "
                    f"{value:.2f} deg"
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

                self.runtime_yaw = (
                    float(value)
                )

                print(
                    "[RUNTIME] YAW -> "
                    f"{value:.2f} deg"
                )

            return

        # ====================================================
        # ATTITUDE
        # ====================================================

        if command == "attitude":

            if not isinstance(
                value,
                dict,
            ):

                return

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

                print(
                    "[RUNTIME] ATTITUDE UPDATED"
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

                self.runtime_battery = (
                    float(value)
                )

                print(
                    "[RUNTIME] BATTERY -> "
                    f"{value:.1f}%"
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
                    "[RUNTIME] GPS UPDATED"
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
                "[RUNTIME] ARM -> "
                f"{result}"
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
                "[RUNTIME] DISARM -> "
                f"{result}"
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
                "[RUNTIME] TAKEOFF "
                f"{value}m -> "
                f"{result}"
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
                "[RUNTIME] LAND -> "
                f"{result}"
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
                "[RUNTIME] RTL -> "
                f"{result}"
            )

            return

        # ====================================================
        # ADD WAYPOINT
        # ====================================================

        if command == "add_waypoint":

            if not isinstance(
                value,
                dict,
            ):

                return

            action = value.get(
                "action",
                "waypoint",
            )

            latitude = value.get("latitude")
            longitude = value.get("longitude")
            altitude = value.get("altitude")

            if action == "rtl":

                home = self.drone.get_home_position()

                latitude = home["lat"]
                longitude = home["lon"]
                altitude = home["alt"]

            waypoint = (
                self.drone.mission.add_waypoint(
                    latitude=latitude,
                    longitude=longitude,
                    altitude=altitude,
                    speed=value.get(
                        "speed",
                        5.0,
                    ),
                    hold_time=value.get(
                        "hold_time",
                        0.0,
                    ),
                    name=value.get(
                        "name",
                        "RTL" if action == "rtl" else "",
                    ),
                    action=action,
                )
            )

            print(
                "[RUNTIME] WAYPOINT ADDED -> "
                f"#{waypoint.index} "
                f"{waypoint.latitude:.7f}, "
                f"{waypoint.longitude:.7f}, "
                f"{waypoint.altitude:.1f}m"
            )

            return

        # ====================================================
        # CLEAR MISSION
        # ====================================================

        if command == "clear_mission":

            self.drone.mission.clear()

            print(
                "[RUNTIME] MISSION CLEARED"
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
                "[RUNTIME] START MISSION -> "
                f"{result}"
            )

            return

        # ====================================================
        # SET MISSION SPEED
        #
        # Applies to every waypoint currently in the mission,
        # including the one being flown right now.
        # ====================================================

        if command == "set_mission_speed":

            try:

                speed = max(
                    0.0,
                    float(value),
                )

            except Exception:

                return

            for waypoint in (
                self.drone.mission.get_all()
            ):

                waypoint.speed = speed

            current_waypoint = (
                self.drone.mission
                .get_current_waypoint()
            )

            if (
                current_waypoint is not None
                and self.drone.mission_navigator.is_active()
            ):

                self.drone.flight_model.set_target_speed(
                    speed
                )

            print(
                "[RUNTIME] MISSION SPEED -> "
                f"{speed:.1f} m/s"
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
                "[RUNTIME] STOP MISSION -> "
                f"{result}"
            )

            return

        # ====================================================
        # UNKNOWN
        # ====================================================

        print(
            "[RUNTIME] UNKNOWN COMMAND -> "
            f"{command}"
        )

    # ========================================================
    # RUN
    # ========================================================

    def run(
        self,
    ):

        if self.running:

            return

        self.running = True

        try:

            print()
            print("======================================")
            print("      MAVLINK DRONE SIMULATOR")
            print("======================================")
            print(
                "[SIM] Simulation worker starting..."
            )
            print()

            # ==================================================
            # DRONE CONFIG
            # ==================================================

            latitude = self._get_float(
                self.drone_config,
                "lat",
                self.mavlink_config.get(
                    "home_lat",
                    10.8231000,
                ),
            )

            longitude = self._get_float(
                self.drone_config,
                "lon",
                self.mavlink_config.get(
                    "home_lon",
                    106.6297000,
                ),
            )

            altitude = self._get_float(
                self.drone_config,
                "alt",
                self.mavlink_config.get(
                    "home_alt",
                    0.0,
                ),
            )

            print(
                f"[SIM] Home latitude  : "
                f"{latitude:.7f}"
            )

            print(
                f"[SIM] Home longitude : "
                f"{longitude:.7f}"
            )

            print(
                f"[SIM] Home altitude  : "
                f"{altitude:.2f} m"
            )

            # ==================================================
            # CREATE DRONE
            # ==================================================

            print()
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
            # FLIGHT CONTROLLER
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

            system_id = self._get_int(
                self.mavlink_config,
                "system_id",
                1,
            )

            component_id = self._get_int(
                self.mavlink_config,
                "component_id",
                1,
            )

            # --------------------------------------------------
            # TX
            # --------------------------------------------------

            tx_host = str(
                self.mavlink_config.get(
                    "tx_host",
                    "127.0.0.1",
                )
            ).strip()

            tx_port = self._get_int(
                self.mavlink_config,
                "tx_port",
                14550,
            )

            # --------------------------------------------------
            # RX
            # --------------------------------------------------

            rx_host = str(
                self.mavlink_config.get(
                    "rx_host",
                    "0.0.0.0",
                )
            ).strip()

            rx_port = self._get_int(
                self.mavlink_config,
                "rx_port",
                14551,
            )

            # --------------------------------------------------
            # Telemetry rate compatibility
            # --------------------------------------------------

            telemetry_rate = self._get_float(
                self.mavlink_config,
                "telemetry_rate_hz",
                self.mavlink_config.get(
                    "telemetry_rate",
                    20.0,
                ),
            )

            if telemetry_rate <= 0.0:

                telemetry_rate = 20.0

            # ==================================================
            # MAVLINK CONFIG PRINT
            # ==================================================

            print()
            print("======================================")
            print("          MAVLINK CONFIG")
            print("======================================")

            print(
                f"[MAVLINK] System ID     : "
                f"{system_id}"
            )

            print(
                f"[MAVLINK] Component ID  : "
                f"{component_id}"
            )

            print(
                f"[MAVLINK] TX -> GCS     : "
                f"{tx_host}:{tx_port}"
            )

            print(
                f"[MAVLINK] RX <- GCS     : "
                f"{rx_host}:{rx_port}"
            )

            print(
                f"[MAVLINK] Config rate   : "
                f"{telemetry_rate:.2f} Hz"
            )

            print("======================================")
            print()

            # ==================================================
            # MAVLINK CONNECTION
            # ==================================================

            print(
                "[SIM] Creating MAVLink connection..."
            )

            connection_string = (
                f"udp:{tx_host}:{tx_port}"
            )

            self.mavlink = MAVLinkConnection(
                connection_string=connection_string,
                source_system=system_id,
                source_component=component_id,
                rx_host=rx_host,
                rx_port=rx_port,
            )

            self.mavlink.connect()

            print(
                "[SIM] MAVLink connection OK"
            )

            # ==================================================
            # MISSION RECEIVER
            # ==================================================

            print(
                "[SIM] Creating MissionReceiver..."
            )

            self.mission_receiver = MissionReceiver(
                connection=self.mavlink,
                mission=self.drone.mission,
                system_id=system_id,
                component_id=component_id,
                get_home_position=self.drone.get_home_position,
            )

            print(
                "[SIM] MissionReceiver OK"
            )

            # ==================================================
            # COMMAND RECEIVER
            # ==================================================

            print(
                "[SIM] Creating CommandReceiver..."
            )

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

            print(
                "[SIM] Creating MAVLinkTelemetry..."
            )

            self.telemetry = MAVLinkTelemetry(
                drone=self.drone,
                connection=self.mavlink,
                system_id=system_id,
                component_id=component_id,
            )

            print(
                "[SIM] MAVLinkTelemetry OK"
            )

            # ==================================================
            # INITIAL RUNTIME STATUS
            # ==================================================

            self.runtime_mode = (
                self.drone.get_mode()
            )

            self.runtime_altitude = (
                altitude
            )

            self.runtime_speed = 0.0

            self.runtime_heading = float(
                getattr(
                    self.drone.state,
                    "heading",
                    0.0,
                )
            )

            self.runtime_latitude = (
                latitude
            )

            self.runtime_longitude = (
                longitude
            )

            self.runtime_roll = 0.0

            self.runtime_pitch = 0.0

            self.runtime_yaw = 0.0

            self.runtime_battery = 100.0

            # ==================================================
            # READY
            # ==================================================

            print()
            print("======================================")
            print("        SIMULATOR READY")
            print("======================================")

            print(
                f"[SIM] Drone SYSID      : "
                f"{system_id}"
            )

            print(
                f"[SIM] Drone COMPID     : "
                f"{component_id}"
            )

            print(
                f"[SIM] MAVLink TX       : "
                f"{tx_host}:{tx_port}"
            )

            print(
                f"[SIM] MAVLink RX       : "
                f"{rx_host}:{rx_port}"
            )

            print(
                "[SIM] Waiting for "
                "Ground Station..."
            )

            print(
                "[SIM] Runtime control enabled"
            )

            print(
                "======================================"
            )
            print()

            self.status_changed.emit(
                "RUNNING"
            )

            # ==================================================
            # SIMULATION CLOCK
            # ==================================================

            last_time = time.monotonic()

            # ==================================================
            # SIMULATION LOOP
            # ==================================================

            while self.running:

                # ------------------------------------------------
                # DELTA TIME
                # ------------------------------------------------

                now = time.monotonic()

                dt = (
                    now - last_time
                )

                last_time = now

                if dt < 0.0:

                    dt = 0.0

                elif dt > 0.1:

                    dt = 0.1

                # ==================================================
                # RUNTIME COMMANDS
                # ==================================================

                self._process_runtime_commands()

                # ==================================================
                # MAVLINK RX
                # ==================================================

                self._process_mavlink_messages()

                # ==================================================
                # MISSION TABLE SYNC
                # ==================================================

                self._sync_mission_table()

                # ==================================================
                # DRONE PHYSICS
                # ==================================================

                if (
                    self.drone is not None
                    and self.running
                ):

                    try:

                        self.drone.update(
                            dt
                        )

                    except Exception as exc:

                        print(
                            "[DRONE UPDATE ERROR] "
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        )

                # ==================================================
                # MAVLINK TELEMETRY
                # ==================================================

                if (
                    self.telemetry is not None
                    and self.running
                ):

                    try:

                        self.telemetry.update()

                    except Exception as exc:

                        print(
                            "[TELEMETRY UPDATE ERROR] "
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        )

                # ==================================================
                # GUI TELEMETRY
                # ==================================================

                if (
                    self.drone is not None
                    and self.running
                ):

                    try:

                        status = (
                            self.drone.get_status()
                        )

                        if isinstance(
                            status,
                            dict,
                        ):

                            self.telemetry_updated.emit(
                                status
                            )

                    except Exception as exc:

                        print(
                            "[GUI TELEMETRY ERROR] "
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        )

                # ==================================================
                # SIMULATION LOOP
                # ==================================================

                time.sleep(
                    0.01
                )

        except Exception as exc:

            error_message = (
                f"{type(exc).__name__}: {exc}"
            )

            print()
            print(
                "======================================"
            )

            print(
                "       SIMULATION ERROR"
            )

            print(
                "======================================"
            )

            print(
                error_message
            )

            print(
                "======================================"
            )

            traceback.print_exc()

            try:

                self.error_occurred.emit(
                    error_message
                )

                self.status_changed.emit(
                    "ERROR"
                )

            except Exception:

                pass

        finally:

            self._cleanup()

    # ========================================================
    # MAVLINK RX
    # ========================================================

    def _process_mavlink_messages(
        self,
    ):

        if not self.running:

            return

        if self.mavlink is None:

            return

        # ----------------------------------------------------
        # Limit messages per cycle so a GCS flood cannot
        # block physics.
        # ----------------------------------------------------

        max_messages = 100

        processed = 0

        while (
            self.running
            and
            processed < max_messages
        ):

            try:

                message = (
                    self.mavlink.receive(
                        blocking=False
                    )
                )

            except Exception as exc:

                print(
                    "[MAVLINK RX ERROR] "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                break

            if message is None:

                break

            processed += 1

            try:

                message_type = (
                    message.get_type()
                )

            except Exception:

                message_type = "UNKNOWN"

            # ------------------------------------------------
            # Ignore parser garbage.
            # ------------------------------------------------

            if message_type in (
                "BAD_DATA",
                "UNKNOWN",
            ):

                continue

            print(
                f"[MAVLINK RX] "
                f"{message_type}"
            )

            # =================================================
            # MISSION
            # =================================================

            if (
                self.mission_receiver
                is not None
            ):

                try:

                    self.mission_receiver.process(
                        message
                    )

                except Exception as exc:

                    print(
                        "[MISSION RX ERROR] "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

            # =================================================
            # COMMAND
            # =================================================

            if (
                self.command_receiver
                is not None
            ):

                try:

                    self.command_receiver.process(
                        message
                    )

                except Exception as exc:

                    print(
                        "[COMMAND RX ERROR] "
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

    # ========================================================
    # MISSION TABLE SYNC
    #
    # Emits the current waypoint list whenever it changes,
    # so the GUI mission table stays in sync with missions
    # uploaded from an external GCS (e.g. Mission Planner /
    # QGroundControl), not only ones added from the GUI.
    # ========================================================

    def _sync_mission_table(self):

        if self.drone is None:

            return

        try:

            waypoints = (
                self.drone.mission.get_all()
            )

        except Exception:

            return

        waypoint_list = [
            {
                "index": wp.index,
                "name": wp.name,
                "action": wp.action,
                "latitude": wp.latitude,
                "longitude": wp.longitude,
                "altitude": wp.altitude,
                "speed": wp.speed,
            }
            for wp in waypoints
        ]

        snapshot = {
            "waypoints": waypoint_list,
            "current_index": (
                self.drone.mission.get_current_index()
            ),
            "active": (
                self.drone.mission_navigator.is_active()
            ),
            "finished": (
                self.drone.mission.is_finished()
            ),
        }

        if snapshot == self._last_mission_snapshot:

            return

        self._last_mission_snapshot = snapshot

        self.mission_updated.emit(snapshot)

    # ========================================================
    # CONFIG HELPERS
    # ========================================================

    @staticmethod
    def _get_int(
        config,
        key,
        default,
    ):

        try:

            return int(
                config.get(
                    key,
                    default,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            return int(
                default
            )

    # ========================================================

    @staticmethod
    def _get_float(
        config,
        key,
        default,
    ):

        try:

            return float(
                config.get(
                    key,
                    default,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            return float(
                default
            )

    # ========================================================
    # STOP
    # ========================================================

    def stop(
        self,
    ):

        if not self.running:

            return

        print(
            "[SIM] Stop requested"
        )

        self.running = False

    # ========================================================
    # CLEAR COMMAND QUEUE
    # ========================================================

    def _clear_command_queue(
        self,
    ):

        while True:

            try:

                self.command_queue.get_nowait()

                self.command_queue.task_done()

            except queue.Empty:

                break

    # ========================================================
    # CLEANUP
    # ========================================================

    def _cleanup(
        self,
    ):

        self.running = False

        print(
            "[SIM] Cleaning up..."
        )

        # ====================================================
        # RUNTIME QUEUE
        # ====================================================

        self._clear_command_queue()

        # ====================================================
        # MAVLINK
        # ====================================================

        if self.mavlink is not None:

            try:

                self.mavlink.close()

            except Exception as exc:

                print(
                    "[MAVLINK CLOSE ERROR] "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

        # ====================================================
        # RELEASE OBJECTS
        # ====================================================

        self.telemetry = None

        self.command_receiver = None

        self.mission_receiver = None

        self.mavlink = None

        self.controller = None

        self.drone = None

        # ====================================================
        # RUNTIME VALUES
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

        print(
            "[SIM] Worker finished"
        )

        try:

            self.status_changed.emit(
                "STOPPED"
            )

        except Exception:

            pass