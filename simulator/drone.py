from core.state import DroneState
from simulation.flight_model import FlightModel


class Drone:

    def __init__(
        self,
        lat=10.8231000,
        lon=106.6297000,
        alt=0.0,
    ):

        # ====================================================
        # STATE
        # ====================================================

        self.state = DroneState(
            lat=lat,
            lon=lon,
            alt=alt,
        )

        # ====================================================
        # FLIGHT MODEL
        # ====================================================

        self.flight_model = (
            FlightModel()
        )

    # ========================================================
    # ARM
    # ========================================================

    def arm(self):

        with self.state.lock:

            self.state.armed = True

            self.state.mode = "GUIDED"

    # ========================================================
    # DISARM
    # ========================================================

    def disarm(self):

        with self.state.lock:

            self.state.armed = False

            self.state.mode = "STANDBY"

    # ========================================================
    # TAKEOFF
    # ========================================================

    def takeoff(
        self,
        altitude,
    ):

        if not self.state.armed:

            return

        self.flight_model.set_target_altitude(
            altitude
        )

        self.state.airborne = True

        self.state.mode = "GUIDED"

    # ========================================================
    # LAND
    # ========================================================

    def land(self):

        self.flight_model.set_target_altitude(
            0.0
        )

    # ========================================================
    # SET SPEED
    # ========================================================

    def set_speed(
        self,
        speed,
    ):

        self.flight_model.set_target_speed(
            speed
        )

    # ========================================================
    # SET HEADING
    # ========================================================

    def set_heading(
        self,
        heading,
    ):

        self.flight_model.set_target_heading(
            heading
        )

    # ========================================================
    # SET ALTITUDE
    # ========================================================

    def set_altitude(
        self,
        altitude,
    ):

        self.flight_model.set_target_altitude(
            altitude
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        dt,
    ):

        with self.state.lock:

            self.state.sim_time += dt

            self.flight_model.update(
                self.state,
                dt,
            )

            self._update_battery(
                dt
            )

            if (
                self.state.alt <= 0.01
                and
                self.flight_model.target_altitude <= 0
            ):

                self.state.airborne = False

    # ========================================================
    # BATTERY
    # ========================================================

    def _update_battery(
        self,
        dt,
    ):

        # Approximate consumption

        base_consumption = 0.002

        flight_consumption = (
            self.state.ground_speed
            * 0.0002
        )

        consumption = (
            base_consumption
            + flight_consumption
        ) * dt

        self.state.battery = max(
            0.0,
            self.state.battery
            - consumption,
        )

        # Approximate voltage

        self.state.voltage = (
            14.0
            + (
                self.state.battery
                / 100.0
            ) * 2.8
        )

        self.state.current = (
            2.0
            + self.state.ground_speed
            * 0.3
        )

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self):

        return self.state.get_status()