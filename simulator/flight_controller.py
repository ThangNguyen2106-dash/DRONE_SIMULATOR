class FlightController:

    def __init__(
        self,
        drone,
    ):

        self.drone = drone

    # ========================================================
    # ARM
    # ========================================================

    def arm(self):

        return self.drone.arm()

    # ========================================================
    # DISARM
    # ========================================================

    def disarm(self):

        return self.drone.disarm()

    # ========================================================
    # TAKEOFF
    # ========================================================

    def takeoff(
        self,
        altitude,
    ):

        return self.drone.takeoff(
            altitude
        )

    # ========================================================
    # LAND
    # ========================================================

    def land(self):

        return self.drone.land()

    # ========================================================
    # HOLD
    # ========================================================

    def hold(self):

        self.drone.stop_mission()

    # ========================================================
    # SET ALTITUDE
    # ========================================================

    def set_altitude(
        self,
        altitude,
    ):

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
    # MISSION
    # ========================================================

    def add_waypoint(
        self,
        latitude,
        longitude,
        altitude,
        speed=5.0,
        hold_time=0.0,
        name="",
    ):

        return self.drone.add_waypoint(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            speed=speed,
            hold_time=hold_time,
            name=name,
        )

    # ========================================================

    def clear_mission(self):

        self.drone.clear_mission()

    # ========================================================

    def start_mission(self):

        return self.drone.start_mission()

    # ========================================================

    def stop_mission(self):

        self.drone.stop_mission()

    # ========================================================
    # EMERGENCY STOP
    # ========================================================

    def emergency_stop(self):

        self.drone.stop_mission()

        self.drone.disarm()

    def rtl(self):
        
        return self.drone.rtl() 