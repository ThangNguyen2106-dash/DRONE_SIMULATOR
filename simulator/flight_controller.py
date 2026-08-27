class FlightController:

    def __init__(self, drone):

        self.drone = drone

    # ========================================================
    # ARM
    # ========================================================

    def arm(self):

        self.drone.arm()

    # ========================================================
    # DISARM
    # ========================================================

    def disarm(self):

        self.drone.disarm()

    # ========================================================
    # TAKEOFF
    # ========================================================

    def takeoff(self, altitude):

        if altitude <= 0:

            raise ValueError(
                "Takeoff altitude must be greater than 0"
            )

        self.drone.takeoff(
            altitude
        )

    # ========================================================
    # LAND
    # ========================================================

    def land(self):

        self.drone.land()

    # ========================================================
    # HOLD
    # ========================================================

    def hold(self):

        status = self.drone.get_status()

        self.drone.set_speed(
            0.0
        )

        self.drone.set_altitude(
            status["alt"]
        )

    # ========================================================
    # SET ALTITUDE
    # ========================================================

    def set_altitude(
        self,
        altitude,
    ):

        if altitude < 0:

            altitude = 0.0

        self.drone.set_altitude(
            altitude
        )

    # ========================================================
    # SET SPEED
    # ========================================================

    def set_speed(
        self,
        speed,
    ):

        if speed < 0:

            speed = 0.0

        self.drone.set_speed(
            speed
        )

    # ========================================================
    # SET HEADING
    # ========================================================

    def set_heading(
        self,
        heading,
    ):

        heading %= 360.0

        self.drone.set_heading(
            heading
        )

    # ========================================================
    # SET VELOCITY
    # ========================================================

    def set_velocity(
        self,
        speed,
        heading,
    ):

        self.set_speed(
            speed
        )

        self.set_heading(
            heading
        )

    # ========================================================
    # EMERGENCY STOP
    # ========================================================

    def emergency_stop(self):

        self.drone.set_speed(
            0.0
        )

        self.drone.set_altitude(
            self.drone.get_status()["alt"]
        )

        self.drone.disarm()