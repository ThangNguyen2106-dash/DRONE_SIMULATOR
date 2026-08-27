import math


class FlightModel:

    # ========================================================
    # EARTH
    # ========================================================

    EARTH_RADIUS = 6378137.0

    # ========================================================
    # LIMITS
    # ========================================================

    MAX_SPEED = 25.0

    MAX_VERTICAL_SPEED = 5.0

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        self.target_altitude = 0.0

        self.target_speed = 0.0

        self.target_heading = 0.0

        self.vertical_speed = 0.0

        self.ground_speed = 0.0

        self.heading = 0.0

    # ========================================================
    # SET TARGET
    # ========================================================

    def set_target_altitude(
        self,
        altitude,
    ):

        self.target_altitude = max(
            0.0,
            float(altitude),
        )

    # ========================================================

    def set_target_speed(
        self,
        speed,
    ):

        self.target_speed = max(
            0.0,
            min(
                float(speed),
                self.MAX_SPEED,
            ),
        )

    # ========================================================

    def set_target_heading(
        self,
        heading,
    ):

        self.target_heading = (
            float(heading) % 360.0
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        state,
        dt,
    ):

        if dt <= 0:

            return

        # ====================================================
        # ALTITUDE
        # ====================================================

        altitude_error = (
            self.target_altitude
            - state.alt
        )

        desired_vertical_speed = max(
            -self.MAX_VERTICAL_SPEED,
            min(
                altitude_error,
                self.MAX_VERTICAL_SPEED,
            ),
        )

        # Smooth vertical speed
        acceleration = 2.0

        max_delta = (
            acceleration * dt
        )

        delta = (
            desired_vertical_speed
            - self.vertical_speed
        )

        delta = max(
            -max_delta,
            min(
                delta,
                max_delta,
            ),
        )

        self.vertical_speed += delta

        state.vertical_speed = (
            self.vertical_speed
        )

        state.alt += (
            self.vertical_speed * dt
        )

        # Prevent negative altitude

        if state.alt < 0:

            state.alt = 0.0

            self.vertical_speed = 0.0

        # ====================================================
        # HORIZONTAL SPEED
        # ====================================================

        speed_error = (
            self.target_speed
            - self.ground_speed
        )

        acceleration = 3.0

        max_delta = (
            acceleration * dt
        )

        speed_delta = max(
            -max_delta,
            min(
                speed_error,
                max_delta,
            ),
        )

        self.ground_speed += (
            speed_delta
        )

        state.ground_speed = (
            self.ground_speed
        )

        # ====================================================
        # HEADING
        # ====================================================

        heading_error = (
            self.target_heading
            - self.heading
        )

        if heading_error > 180:

            heading_error -= 360

        elif heading_error < -180:

            heading_error += 360

        max_turn_rate = 90.0

        max_heading_delta = (
            max_turn_rate * dt
        )

        heading_delta = max(
            -max_heading_delta,
            min(
                heading_error,
                max_heading_delta,
            ),
        )

        self.heading += (
            heading_delta
        )

        self.heading %= 360.0

        state.heading = (
            self.heading
        )

        state.yaw = (
            self.heading
        )

        # ====================================================
        # NORTH / EAST VELOCITY
        # ====================================================

        heading_rad = math.radians(
            self.heading
        )

        north_speed = (
            self.ground_speed
            * math.cos(heading_rad)
        )

        east_speed = (
            self.ground_speed
            * math.sin(heading_rad)
        )

        state.north_speed = (
            north_speed
        )

        state.east_speed = (
            east_speed
        )

        # ====================================================
        # GPS POSITION
        # ====================================================

        latitude_rad = math.radians(
            state.lat
        )

        meters_per_degree_lat = (
            math.pi
            * self.EARTH_RADIUS
            / 180.0
        )

        meters_per_degree_lon = (
            math.pi
            * self.EARTH_RADIUS
            * math.cos(latitude_rad)
            / 180.0
        )

        if meters_per_degree_lon < 1:

            meters_per_degree_lon = 1

        state.lat += (
            north_speed
            * dt
            / meters_per_degree_lat
        )

        state.lon += (
            east_speed
            * dt
            / meters_per_degree_lon
        )

        # ====================================================
        # ATTITUDE
        # ====================================================

        # Basic simulated pitch

        if self.target_speed > 0:

            state.pitch = min(
                15.0,
                self.ground_speed * 0.5,
            )

        else:

            state.pitch = 0.0

        # Basic simulated roll
        # based on heading change

        state.roll = max(
            -30.0,
            min(
                30.0,
                heading_error * 0.3,
            ),
        )