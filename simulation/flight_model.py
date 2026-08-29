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

    # Maximum visual lean angle shown while under joystick
    # body-frame (tilt-to-move) control.
    MAX_TILT_ANGLE = 25.0

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

        # ====================================================
        # BODY-FRAME (JOYSTICK TILT) CONTROL
        #
        # When active, forward/lateral velocity is commanded
        # directly in the drone's body frame (like a real
        # quadrotor leaning to move) instead of via
        # target_speed + target_heading.
        # ====================================================

        self.body_control_active = False

        self._body_forward_target = 0.0
        self._body_lateral_target = 0.0

        self._body_forward_actual = 0.0
        self._body_lateral_actual = 0.0

        # ====================================================
        # JOYSTICK NUDGE (obstacle avoidance during autopilot)
        #
        # Unlike body_control_active (which fully replaces the
        # target_speed/heading autopilot), a nudge is added on
        # top of whatever the autopilot (mission/RTL) is
        # already commanding — lets the pilot steer slightly
        # around an obstacle without cancelling RTL/mission,
        # matching a real FC's "assist" stick input. Centered
        # stick (0, 0) means zero nudge, i.e. no effect at all.
        # ====================================================

        self._nudge_forward = 0.0
        self._nudge_lateral = 0.0

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
    # SET BODY VELOCITY (JOYSTICK TILT CONTROL)
    # ========================================================

    def set_body_velocity(
        self,
        forward,
        lateral,
    ):
        """
        Command forward/lateral speed directly in the body
        frame, as if the drone leaned to move (pitch -> forward,
        roll -> lateral/strafe), independent of self.heading.
        """

        self._body_forward_target = max(
            -self.MAX_SPEED,
            min(
                float(forward),
                self.MAX_SPEED,
            ),
        )

        self._body_lateral_target = max(
            -self.MAX_SPEED,
            min(
                float(lateral),
                self.MAX_SPEED,
            ),
        )

        self.body_control_active = True

    # ========================================================

    def release_body_velocity(self):
        """
        Hand horizontal movement back to the target_speed /
        target_heading autopilot (mission, RTL, manual speed
        setpoints, ...).
        """

        self.body_control_active = False

        self._body_forward_target = 0.0
        self._body_lateral_target = 0.0

        self._body_forward_actual = 0.0
        self._body_lateral_actual = 0.0

        self.target_speed = 0.0

    # ========================================================
    # SET NUDGE (JOYSTICK ASSIST DURING AUTOPILOT)
    # ========================================================

    # Deliberately much lower than MAX_SPEED — this is meant
    # for a small sidestep around an obstacle, not for flying
    # the mission/RTL leg by hand.
    MAX_NUDGE_SPEED = 4.0

    def set_nudge(
        self,
        forward,
        lateral,
    ):

        self._nudge_forward = max(
            -self.MAX_NUDGE_SPEED,
            min(
                float(forward),
                self.MAX_NUDGE_SPEED,
            ),
        )

        self._nudge_lateral = max(
            -self.MAX_NUDGE_SPEED,
            min(
                float(lateral),
                self.MAX_NUDGE_SPEED,
            ),
        )

    def clear_nudge(self):

        self._nudge_forward = 0.0
        self._nudge_lateral = 0.0

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

        if not self.body_control_active:

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

        if self.body_control_active:

            # ------------------------------------------------
            # Smooth body-frame forward/lateral speed toward
            # the joystick-commanded targets.
            # ------------------------------------------------

            acceleration = 3.0

            max_delta = acceleration * dt

            forward_delta = max(
                -max_delta,
                min(
                    self._body_forward_target
                    - self._body_forward_actual,
                    max_delta,
                ),
            )

            lateral_delta = max(
                -max_delta,
                min(
                    self._body_lateral_target
                    - self._body_lateral_actual,
                    max_delta,
                ),
            )

            self._body_forward_actual += (
                forward_delta
            )

            self._body_lateral_actual += (
                lateral_delta
            )

            self.ground_speed = math.hypot(
                self._body_forward_actual,
                self._body_lateral_actual,
            )

            state.ground_speed = (
                self.ground_speed
            )

            north_speed = (
                self._body_forward_actual
                * math.cos(heading_rad)
                - self._body_lateral_actual
                * math.sin(heading_rad)
            )

            east_speed = (
                self._body_forward_actual
                * math.sin(heading_rad)
                + self._body_lateral_actual
                * math.cos(heading_rad)
            )

        else:

            north_speed = (
                self.ground_speed
                * math.cos(heading_rad)
            )

            east_speed = (
                self.ground_speed
                * math.sin(heading_rad)
            )

            # Joystick "nudge" (obstacle avoidance during
            # mission/RTL): added on top of the autopilot's own
            # velocity instead of replacing it, so a centered
            # stick (0, 0) leaves navigation completely
            # unaffected.

            if (
                self._nudge_forward != 0.0
                or self._nudge_lateral != 0.0
            ):

                north_speed += (
                    self._nudge_forward
                    * math.cos(heading_rad)
                    - self._nudge_lateral
                    * math.sin(heading_rad)
                )

                east_speed += (
                    self._nudge_forward
                    * math.sin(heading_rad)
                    + self._nudge_lateral
                    * math.cos(heading_rad)
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

        if self.body_control_active:

            # Lean angle directly reflects the joystick's
            # commanded body-frame velocity (pitch = forward,
            # roll = lateral/strafe), like a real quadrotor.

            state.pitch = max(
                -self.MAX_TILT_ANGLE,
                min(
                    self.MAX_TILT_ANGLE,
                    (
                        self._body_forward_actual
                        / self.MAX_SPEED
                    )
                    * self.MAX_TILT_ANGLE,
                ),
            )

            state.roll = max(
                -self.MAX_TILT_ANGLE,
                min(
                    self.MAX_TILT_ANGLE,
                    (
                        self._body_lateral_actual
                        / self.MAX_SPEED
                    )
                    * self.MAX_TILT_ANGLE,
                ),
            )

        else:

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