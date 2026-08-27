import time

from PySide6.QtCore import QThread, Signal
from simulator.flight_controller import FlightController
from simulator.drone import Drone
from mavlink.connection import MAVLinkConnection
from mavlink.telemetry import MAVLinkTelemetry


class SimulationWorker(QThread):

    # ========================================================
    # Signals
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

        self.running = False

        self.drone = None
        
        self.controller = FlightController(
            self.drone
        )

        self.mavlink = None

        self.telemetry = None

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        self.running = True

        try:

            # ==================================================
            # CREATE DRONE
            # ==================================================

            self.drone = Drone(
                lat=self.drone_config.get(
                    "lat",
                    10.8231000,
                ),
                lon=self.drone_config.get(
                    "lon",
                    106.6297000,
                ),
                alt=self.drone_config.get(
                    "alt",
                    0.0,
                ),
            )

            # ==================================================
            # MAVLINK CONFIG
            # ==================================================

            connection_string = (
                self.mavlink_config.get(
                    "connection_string",
                    "udpout:127.0.0.1:14550",
                )
            )

            system_id = (
                self.mavlink_config.get(
                    "system_id",
                    1,
                )
            )

            component_id = (
                self.mavlink_config.get(
                    "component_id",
                    1,
                )
            )

            # ==================================================
            # MAVLINK CONNECTION
            # ==================================================

            self.mavlink = MAVLinkConnection(
                connection_string=connection_string,
                source_system=system_id,
                source_component=component_id,
            )

            self.mavlink.connect()

            # ==================================================
            # TELEMETRY
            # ==================================================

            self.telemetry = MAVLinkTelemetry(
                drone=self.drone,
                connection=self.mavlink,
                system_id=system_id,
                component_id=component_id,
            )

            # ==================================================
            # DRONE INITIALIZATION
            # ==================================================

            self.drone.arm()

            takeoff_altitude = (
                self.drone_config.get(
                    "takeoff_altitude",
                    20.0,
                )
            )

            self.drone.takeoff(
                takeoff_altitude
            )

            self.drone.set_speed(
                self.drone_config.get(
                "speed",
                5.0,
                )
            )

            self.drone.set_heading(
                self.drone_config.get(
                "heading",
                90.0,
                )
            )


            # ==================================================
            # RUNNING
            # ==================================================

            self.status_changed.emit(
                "RUNNING"
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

                # Prevent huge time step
                dt = min(
                    dt,
                    0.1,
                )

                # ----------------------------------------------
                # Update drone
                # ----------------------------------------------

                self.drone.update(
                    dt
                )

                # ----------------------------------------------
                # Send MAVLink telemetry
                # ----------------------------------------------

                self.telemetry.update()

                # ----------------------------------------------
                # Send state to GUI
                # ----------------------------------------------

                status = (
                    self.drone.get_status()
                )

                self.telemetry_updated.emit(
                    status
                )

                # ----------------------------------------------
                # 100 Hz
                # ----------------------------------------------

                time.sleep(
                    0.01
                )

        except Exception as exc:

            message = (
                f"{type(exc).__name__}: {exc}"
            )

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

        # ----------------------------------------------------
        # Close MAVLink
        # ----------------------------------------------------

        if self.mavlink is not None:

            try:

                self.mavlink.close()

            except Exception:
                pass

            self.mavlink = None

        # ----------------------------------------------------
        # Release objects
        # ----------------------------------------------------

        self.telemetry = None

        self.drone = None

        # ----------------------------------------------------
        # Notify GUI
        # ----------------------------------------------------

        self.status_changed.emit(
            "STOPPED"
        )