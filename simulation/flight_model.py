import math


class FlightModel:
    """High-fidelity 6-DOF omnidirectional quadcopter flight dynamics model.

    Features:
      - Full 2D/3D holonomic translation: supports moving in all 8 directions
        (forward, backward, strafe left, strafe right, and all diagonal combinations)
        completely independent of the aircraft's heading (yaw).
      - Realistic aerodynamic tilt dynamics:
          * Pitch reflects forward/backward acceleration and cruise velocity.
          * Roll reflects lateral strafe acceleration and velocity.
          * Coordinated banking during yaw turns.
      - Inertia, active braking, and smooth acceleration curves matching real
        multirotor flight controllers (ArduPilot / PX4).
      - Multi-mode support: Body-frame velocity (8-direction manual/joystick/keyboard),
        World-frame velocity (NED/NE), and Target waypoint/mission navigation.
    """

    # Earth & Environment Constants
    EARTH_RADIUS = 6378137.0
    GRAVITY = 9.81

    # Flight Limits
    MAX_SPEED = 20.0             # Maximum horizontal ground speed (m/s)
    MAX_VERTICAL_SPEED = 5.0    # Maximum climb/descend speed (m/s)
    MAX_TILT_ANGLE = 30.0        # Maximum pitch/roll lean angle (deg)
    MAX_TURN_RATE = 120.0        # Maximum yaw rotation rate (deg/s)

    # Dynamic Accelerations
    ACCEL_HORIZONTAL = 4.5       # Horizontal acceleration (m/s^2)
    DECEL_BRAKING = 6.0          # Active braking deceleration (m/s^2)
    ACCEL_VERTICAL = 3.0         # Vertical acceleration (m/s^2)

    def __init__(self):
        # Targets
        self.target_altitude = 0.0
        self.target_speed = 0.0
        self.target_heading = 0.0

        # Body-frame velocity components (m/s)
        # +forward = Nose forward, -forward = Backward
        # +lateral = Starboard/Right, -lateral = Port/Left
        self._body_forward_target = 0.0
        self._body_lateral_target = 0.0
        self._body_forward_actual = 0.0
        self._body_lateral_actual = 0.0

        # World-frame velocities (m/s)
        self.north_speed = 0.0
        self.east_speed = 0.0
        self.vertical_speed = 0.0
        self.ground_speed = 0.0

        # Attitudes (deg)
        self.heading = 0.0
        self.pitch = 0.0
        self.roll = 0.0

        # Control flags
        self.body_control_active = False

        # Joystick nudge (obstacle avoidance during mission/RTL)
        self._nudge_forward = 0.0
        self._nudge_lateral = 0.0
        self._nudge_climb = 0.0
        self.MAX_NUDGE_SPEED = 4.0

    # ========================================================
    # TARGET SETPOINTS
    # ========================================================

    def set_target_altitude(self, altitude):
        self.target_altitude = max(0.0, float(altitude))

    def set_target_speed(self, speed):
        self.target_speed = max(0.0, min(float(speed), self.MAX_SPEED))

    def set_target_heading(self, heading):
        self.target_heading = float(heading) % 360.0

    # ========================================================
    # 8-DIRECTION BODY VELOCITY CONTROL
    # ========================================================

    def set_body_velocity(self, forward, lateral):
        """Command 8-direction velocity directly in the drone's body frame.

        Parameters:
          forward: Forward (+) or Backward (-) speed in m/s.
          lateral: Strafe Right (+) or Strafe Left (-) speed in m/s.
        """
        self._body_forward_target = max(-self.MAX_SPEED, min(float(forward), self.MAX_SPEED))
        self._body_lateral_target = max(-self.MAX_SPEED, min(float(lateral), self.MAX_SPEED))
        self.body_control_active = True

    def set_direction(self, direction_name, speed=5.0):
        """Convenience method for discrete 8-directional flight."""
        s = max(0.0, min(float(speed), self.MAX_SPEED))
        diag = s * 0.70710678  # 1/sqrt(2)

        dir_map = {
            "FORWARD": (s, 0.0),
            "BACKWARD": (-s, 0.0),
            "LEFT": (0.0, -s),
            "RIGHT": (0.0, s),
            "FORWARD_LEFT": (diag, -diag),
            "FORWARD_RIGHT": (diag, diag),
            "BACKWARD_LEFT": (-diag, -diag),
            "BACKWARD_RIGHT": (-diag, diag),
            "STOP": (0.0, 0.0),
        }

        fwd, lat = dir_map.get(direction_name.upper(), (0.0, 0.0))
        self.set_body_velocity(fwd, lat)

    def release_body_velocity(self):
        """Release body velocity override back to waypoint / autopilot tracking."""
        self.body_control_active = False
        self._body_forward_target = 0.0
        self._body_lateral_target = 0.0
        self.target_speed = 0.0

    # ========================================================
    # NUDGE (COLLISION AVOIDANCE ASSIST)
    # ========================================================

    def set_nudge(self, forward, lateral, climb=0.0):
        """Pilot obstacle avoidance nudge / intervention during autopilot."""
        self._nudge_forward = max(-self.MAX_SPEED, min(float(forward), self.MAX_SPEED))
        self._nudge_lateral = max(-self.MAX_SPEED, min(float(lateral), self.MAX_SPEED))
        self._nudge_climb = max(-self.MAX_VERTICAL_SPEED, min(float(climb), self.MAX_VERTICAL_SPEED))

    def clear_nudge(self):
        self._nudge_forward = 0.0
        self._nudge_lateral = 0.0
        self._nudge_climb = 0.0

    # ========================================================
    # PHYSICS UPDATE LOOP
    # ========================================================

    def update(self, state, dt):
        if dt <= 0.0:
            return

        # If disarmed on ground, freeze all physics and movement
        if not state.armed and state.alt <= 0.01:
            state.alt = 0.0
            state.vertical_speed = 0.0
            state.north_speed = 0.0
            state.east_speed = 0.0
            state.ground_speed = 0.0
            state.pitch = 0.0
            state.roll = 0.0
            self.vertical_speed = 0.0
            self.north_speed = 0.0
            self.east_speed = 0.0
            self.ground_speed = 0.0
            self.pitch = 0.0
            self.roll = 0.0
            self._body_forward_actual = 0.0
            self._body_lateral_actual = 0.0
            return

        # ----------------------------------------------------
        # 1. ALTITUDE & VERTICAL DYNAMICS
        # ----------------------------------------------------
        altitude_error = self.target_altitude - state.alt
        desired_vz = max(-self.MAX_VERTICAL_SPEED, min(altitude_error * 1.5, self.MAX_VERTICAL_SPEED))
        desired_vz += self._nudge_climb

        max_vz_delta = self.ACCEL_VERTICAL * dt
        vz_error = desired_vz - self.vertical_speed
        vz_delta = max(-max_vz_delta, min(vz_error, max_vz_delta))
        self.vertical_speed += vz_delta

        state.vertical_speed = self.vertical_speed
        state.alt += self.vertical_speed * dt

        if state.alt < 0.0:
            state.alt = 0.0
            self.vertical_speed = 0.0

        # ----------------------------------------------------
        # 2. YAW / HEADING DYNAMICS (Always tracks target heading)
        # ----------------------------------------------------
        heading_error = (self.target_heading - self.heading) % 360.0
        if heading_error > 180.0:
            heading_error -= 360.0

        max_turn_delta = self.MAX_TURN_RATE * dt
        heading_delta = max(-max_turn_delta, min(heading_error * 2.5, max_turn_delta))
        self.heading = (self.heading + heading_delta) % 360.0

        state.heading = self.heading
        state.yaw = self.heading

        # ----------------------------------------------------
        # 3. HORIZONTAL & 8-DIRECTION VELOCITY DYNAMICS
        # ----------------------------------------------------
        heading_rad = math.radians(self.heading)

        if self.body_control_active:
            # Combine Autopilot target velocity + Pilot manual nudge (Obstacle Avoidance Assist)
            total_fwd_cmd = self._body_forward_target + self._nudge_forward
            total_lat_cmd = self._body_lateral_target + self._nudge_lateral

            accel_fwd = self.DECEL_BRAKING if (total_fwd_cmd == 0.0) else self.ACCEL_HORIZONTAL
            accel_lat = self.DECEL_BRAKING if (total_lat_cmd == 0.0) else self.ACCEL_HORIZONTAL

            max_fwd_delta = accel_fwd * dt
            max_lat_delta = accel_lat * dt

            fwd_err = total_fwd_cmd - self._body_forward_actual
            lat_err = total_lat_cmd - self._body_lateral_actual

            self._body_forward_actual += max(-max_fwd_delta, min(fwd_err, max_fwd_delta))
            self._body_lateral_actual += max(-max_lat_delta, min(lat_err, max_lat_delta))

            # Transform Body Velocities to World North / East
            north_speed = (
                self._body_forward_actual * math.cos(heading_rad)
                - self._body_lateral_actual * math.sin(heading_rad)
            )
            east_speed = (
                self._body_forward_actual * math.sin(heading_rad)
                + self._body_lateral_actual * math.cos(heading_rad)
            )

        else:
            # Target Speed Autopilot
            total_speed_cmd = self.target_speed + self._nudge_forward
            accel = self.DECEL_BRAKING if (total_speed_cmd == 0.0) else self.ACCEL_HORIZONTAL
            max_speed_delta = accel * dt
            speed_error = total_speed_cmd - self.ground_speed
            self.ground_speed += max(-max_speed_delta, min(speed_error, max_speed_delta))

            # Compute world velocities
            north_speed = (
                self.ground_speed * math.cos(heading_rad)
                - self._nudge_lateral * math.sin(heading_rad)
            )
            east_speed = (
                self.ground_speed * math.sin(heading_rad)
                + self._nudge_lateral * math.cos(heading_rad)
            )

            self._body_forward_actual = self.ground_speed
            self._body_lateral_actual = self._nudge_lateral

            # Compute forward/lateral components in world space
            north_speed = self.ground_speed * math.cos(heading_rad)
            east_speed = self.ground_speed * math.sin(heading_rad)

            # Convert back to body frame for attitude calculations
            self._body_forward_actual = self.ground_speed
            self._body_lateral_actual = 0.0

            # Joystick Nudge (assist input during autopilot)
            if self._nudge_forward != 0.0 or self._nudge_lateral != 0.0:
                north_speed += (
                    self._nudge_forward * math.cos(heading_rad)
                    - self._nudge_lateral * math.sin(heading_rad)
                )
                east_speed += (
                    self._nudge_forward * math.sin(heading_rad)
                    + self._nudge_lateral * math.cos(heading_rad)
                )
                self._body_forward_actual += self._nudge_forward
                self._body_lateral_actual += self._nudge_lateral

        self.north_speed = north_speed
        self.east_speed = east_speed
        self.ground_speed = math.hypot(north_speed, east_speed)

        state.north_speed = self.north_speed
        state.east_speed = self.east_speed
        state.ground_speed = self.ground_speed

        # ----------------------------------------------------
        # 4. GPS POSITION INTEGRATION
        # ----------------------------------------------------
        lat_rad = math.radians(state.lat)
        m_per_deg_lat = math.pi * self.EARTH_RADIUS / 180.0
        m_per_deg_lon = math.pi * self.EARTH_RADIUS * max(0.1, math.cos(lat_rad)) / 180.0

        state.lat += (self.north_speed * dt) / m_per_deg_lat
        state.lon += (self.east_speed * dt) / m_per_deg_lon

        # ----------------------------------------------------
        # 5. REALISTIC ATTITUDE (PITCH & ROLL TILT DYNAMICS)
        # ----------------------------------------------------
        # Real quadrotor physics:
        #   Pitch tilt: Leaning forward (+) or backward (-) proportional to body forward velocity
        #   Roll tilt: Leaning right (+) or left (-) proportional to body lateral velocity
        #   Coordinated turn bank: Roll bias proportional to turn rate
        speed_ratio_fwd = max(-1.0, min(1.0, self._body_forward_actual / self.MAX_SPEED))
        speed_ratio_lat = max(-1.0, min(1.0, self._body_lateral_actual / self.MAX_SPEED))

        # Dynamic lean angles (Pitch < 0 is nose-down for forward flight)
        target_pitch = -speed_ratio_fwd * self.MAX_TILT_ANGLE
        turn_bank = max(-12.0, min(12.0, heading_delta * 3.0))
        target_roll = speed_ratio_lat * self.MAX_TILT_ANGLE + turn_bank

        # Smooth attitude transition (aerodynamic damping)
        tilt_lerp = 1.0 - (0.001 ** dt)
        self.pitch += (target_pitch - self.pitch) * tilt_lerp
        self.roll += (target_roll - self.roll) * tilt_lerp

        state.pitch = self.pitch
        state.roll = self.roll