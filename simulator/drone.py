from enum import Enum

from core.state import DroneState
from core.navigation import Navigation

from simulation.flight_model import FlightModel

from simulator.mission import Mission
from simulator.mission_navigator import MissionNavigator


# ============================================================
# FLIGHT MODE
# ============================================================

class FlightMode(Enum):

    FREE = "FREE"

    MISSION = "MISSION"

    ALT_HOLD = "ALT_HOLD"


# ============================================================
# DRONE
# ============================================================

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
            lat=float(lat),
            lon=float(lon),
            alt=float(alt),
        )

        # ====================================================
        # HOME
        # ====================================================

        self.home_lat = float(lat)

        self.home_lon = float(lon)

        self.home_alt = float(alt)

        # ====================================================
        # MODE
        # ====================================================

        self.flight_mode = FlightMode.FREE

        # ====================================================
        # RTL
        # ====================================================

        self.rtl_active = False

        # ====================================================
        # FLIGHT MODEL
        # ====================================================

        self.flight_model = FlightModel()

        # ====================================================
        # NAVIGATION
        # ====================================================

        self.navigation = Navigation(
            arrival_radius_m=2.0,
            altitude_tolerance_m=1.0,
        )

        # ====================================================
        # MISSION
        # ====================================================

        self.mission = Mission()

        self.mission_navigator = (
            MissionNavigator(
                mission=self.mission,
                navigation=self.navigation,
            )
        )

    # ========================================================
    # MODE
    # ========================================================

    def set_mode(
        self,
        mode,
    ) -> bool:
        """Change the simulator flight mode safely."""
        if isinstance(mode, FlightMode):
            new_mode = mode
        elif isinstance(mode, str):
            mode_text = mode.strip().upper()
            aliases = {
                "FREE_FLIGHT": "FREE",
                "GUIDED": "FREE",
                "ALTITUDE_HOLD": "ALT_HOLD",
                "ALTITUDE HOLD": "ALT_HOLD",
                "AUTO": "MISSION",
            }
            mode_text = aliases.get(mode_text, mode_text)
            try:
                new_mode = FlightMode(mode_text)
            except ValueError:
                return False
        else:
            return False

        with self.state.lock:
            if new_mode == FlightMode.MISSION:
                if self.mission.count() <= 0:
                    # AUTO can be selected before upload; execution starts
                    # automatically once a mission is available.
                    self.flight_mode = FlightMode.MISSION
                    self.state.mode = "AUTO"
                    self.rtl_active = False
                    return True

                self.rtl_active = False
                self.flight_mode = FlightMode.MISSION
                self.state.mode = "AUTO"

                if self.state.armed and not self.mission_navigator.is_active():
                    if not self.mission_navigator.start():
                        return False
                    self.state.airborne = True
                return True

            # Any non-mission mode stops mission execution.
            self.mission_navigator.stop()
            self.rtl_active = False

            if new_mode == FlightMode.FREE:
                self.flight_mode = FlightMode.FREE
                self.state.mode = "GUIDED"
                return True

            if new_mode == FlightMode.ALT_HOLD:
                self.flight_mode = FlightMode.ALT_HOLD
                self.state.mode = "ALT_HOLD"
                return True

        return False

    # ========================================================

    def get_mode(
        self,
    ) -> str:

        return self.flight_mode.value

    # ========================================================
    # FREE FLIGHT
    # ========================================================

    def set_free_flight(
        self,
    ) -> bool:

        return self.set_mode(
            FlightMode.FREE
        )

    # ========================================================
    # ALTITUDE HOLD
    # ========================================================

    def set_altitude_hold(
        self,
        altitude,
    ) -> bool:

        try:

            altitude = float(
                altitude
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        if altitude < 0.0:

            return False

        if not self.state.armed:

            return False

        with self.state.lock:

            self.mission_navigator.stop()

            self.rtl_active = False

            self.flight_model.set_target_altitude(
                altitude
            )

            self.flight_mode = (
                FlightMode.ALT_HOLD
            )

            self.state.mode = "ALT_HOLD"

            self.state.airborne = (
                altitude > 0.01
                or
                self.state.alt > 0.01
            )

        return True

    # ========================================================
    # ARM
    # ========================================================

    def arm(
        self,
    ) -> bool:

        with self.state.lock:

            if self.state.armed:

                return True

            self.state.armed = True

            # ------------------------------------------------
            # Automatically start mission if MISSION mode
            # was selected before ARM.
            # ------------------------------------------------

            if (
                self.flight_mode == FlightMode.MISSION
                and
                self.mission.count() > 0
            ):

                if not self.mission_navigator.is_active():

                    self.mission_navigator.start()

                self.state.mode = "AUTO"

                self.state.airborne = True

            if self.state.mode in (
                "STANDBY",
                "DISARMED",
            ):

                self.state.mode = "GUIDED"

            return True

    # ========================================================
    # DISARM
    # ========================================================

    def disarm(
        self,
    ) -> bool:

        with self.state.lock:

            # Do not allow airborne disarm.
            if self.state.airborne:

                return False

            self.state.armed = False

            self.state.mode = "STANDBY"

            self.rtl_active = False

            self.mission_navigator.stop()

            self.flight_mode = (
                FlightMode.FREE
            )

            return True

    # ========================================================
    # TAKEOFF
    # ========================================================

    def takeoff(
        self,
        altitude,
    ) -> bool:

        try:

            altitude = float(
                altitude
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        if altitude <= 0.0:

            return False

        if not self.state.armed:

            return False

        with self.state.lock:

            # ------------------------------------------------
            # Cancel RTL
            # ------------------------------------------------

            self.rtl_active = False

            # ------------------------------------------------
            # Cancel mission
            # ------------------------------------------------

            self.mission_navigator.stop()

            # ------------------------------------------------
            # FREE/GUIDED operation
            # ------------------------------------------------

            self.flight_mode = (
                FlightMode.FREE
            )

            self.flight_model.set_target_altitude(
                altitude
            )

            self.state.airborne = True

            self.state.mode = "GUIDED"

        return True

    # ========================================================
    # LAND
    # ========================================================

    def land(
        self,
    ) -> bool:

        if not self.state.armed:

            return False

        with self.state.lock:

            # ------------------------------------------------
            # Stop mission
            # ------------------------------------------------

            self.mission_navigator.stop()

            # ------------------------------------------------
            # Stop RTL
            # ------------------------------------------------

            self.rtl_active = False

            # ------------------------------------------------
            # FREE mode after landing command
            # ------------------------------------------------

            self.flight_mode = (
                FlightMode.FREE
            )

            # ------------------------------------------------
            # Stop horizontal movement
            # ------------------------------------------------

            self.flight_model.set_target_speed(
                0.0
            )

            # ------------------------------------------------
            # Descend to zero
            # ------------------------------------------------

            self.flight_model.set_target_altitude(
                0.0
            )

            self.state.mode = "LAND"

        return True

    # ========================================================
    # SET BODY VELOCITY (JOYSTICK TILT CONTROL)
    # ========================================================

    def set_body_velocity(
        self,
        forward,
        lateral,
    ) -> bool:

        try:

            forward = float(
                forward
            )

            lateral = float(
                lateral
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        if not self.state.armed:

            return False

        # While a mission or RTL is actively navigating, don't
        # let the joystick fully replace it (that's the old
        # body_control_active behavior and would stall/derail
        # the autopilot the instant the stick recenters to
        # 0, 0 — every tick, since the panel keeps sending this
        # continuously). Instead treat the stick as a small
        # obstacle-avoidance nudge added on top of the
        # autopilot's own velocity; RTL/mission keep navigating
        # underneath it.
        #
        # Note: rtl() switches flight_mode back to FREE (it
        # navigates via rtl_active + navigation.set_target, not
        # a dedicated FlightMode), so rtl_active must be checked
        # separately here.

        autopilot_active = (
            self.flight_mode == FlightMode.MISSION
            or self.rtl_active
        )

        with self.state.lock:

            if autopilot_active:

                self.flight_model.set_nudge(
                    forward,
                    lateral,
                )

            else:

                self.flight_model.set_body_velocity(
                    forward,
                    lateral,
                )

        return True

    # ========================================================
    # RELEASE BODY VELOCITY CONTROL
    # ========================================================

    def release_body_control(
        self,
    ) -> bool:

        with self.state.lock:

            self.flight_model.release_body_velocity()

            self.flight_model.clear_nudge()

        return True

    # ========================================================
    # SET SPEED
    # ========================================================

    def set_speed(
        self,
        speed,
    ) -> bool:

        try:

            speed = float(
                speed
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        if speed < 0.0:

            return False

        if not self.state.armed:

            return False

        with self.state.lock:

            self.flight_model.set_target_speed(
                speed
            )

        return True

    # ========================================================
    # SET HEADING
    # ========================================================

    def set_heading(
        self,
        heading,
    ) -> bool:

        try:

            heading = float(
                heading
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        heading %= 360.0

        if not self.state.armed:

            return False

        with self.state.lock:

            self.flight_model.set_target_heading(
                heading
            )

        return True

    # ========================================================
    # SET ALTITUDE
    # ========================================================

    def set_altitude(
        self,
        altitude,
    ) -> bool:

        try:

            altitude = float(
                altitude
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        if altitude < 0.0:

            return False

        if not self.state.armed:

            return False

        with self.state.lock:

            self.flight_model.set_target_altitude(
                altitude
            )

        return True

    # ========================================================
    # SET POSITION
    #
    # Runtime position override.
    #
    # This changes the simulated position immediately.
    # Useful for testing a GCS/application.
    # ========================================================

    def set_position(
        self,
        lat,
        lon,
        alt=None,
    ) -> bool:

        try:

            lat = float(lat)

            lon = float(lon)

        except (
            TypeError,
            ValueError,
        ):

            return False

        if not (
            -90.0
            <= lat
            <= 90.0
        ):

            return False

        if not (
            -180.0
            <= lon
            <= 180.0
        ):

            return False

        with self.state.lock:

            self.state.lat = lat

            self.state.lon = lon

            if alt is not None:

                try:

                    alt = float(
                        alt
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

                if alt < 0.0:

                    return False

                self.state.alt = alt

                self.state.airborne = (
                    alt > 0.01
                )

        return True

    # ========================================================
    # SET LATITUDE
    # ========================================================

    def set_latitude(
        self,
        latitude,
    ) -> bool:

        with self.state.lock:

            longitude = self.state.lon

        return self.set_position(
            latitude,
            longitude,
        )

    # ========================================================
    # SET LONGITUDE
    # ========================================================

    def set_longitude(
        self,
        longitude,
    ) -> bool:

        with self.state.lock:

            latitude = self.state.lat

        return self.set_position(
            latitude,
            longitude,
        )

    # ========================================================
    # SET ATTITUDE
    # ========================================================

    def set_attitude(
        self,
        roll=None,
        pitch=None,
        yaw=None,
    ) -> bool:

        with self.state.lock:

            if roll is not None:

                try:

                    self.state.roll = float(
                        roll
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

            if pitch is not None:

                try:

                    self.state.pitch = float(
                        pitch
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

            if yaw is not None:

                try:

                    yaw = float(
                        yaw
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

                yaw %= 360.0

                self.state.yaw = yaw

                self.flight_model.set_target_heading(
                    yaw
                )

        return True

    # ========================================================
    # SET ROLL
    # ========================================================

    def set_roll(
        self,
        roll,
    ) -> bool:

        return self.set_attitude(
            roll=roll
        )

    # ========================================================
    # SET PITCH
    # ========================================================

    def set_pitch(
        self,
        pitch,
    ) -> bool:

        return self.set_attitude(
            pitch=pitch
        )

    # ========================================================
    # SET YAW
    # ========================================================

    def set_yaw(
        self,
        yaw,
    ) -> bool:

        return self.set_attitude(
            yaw=yaw
        )

    # ========================================================
    # SET BATTERY
    # ========================================================

    def set_battery(
        self,
        percentage,
    ) -> bool:

        try:

            percentage = float(
                percentage
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        percentage = max(
            0.0,
            min(
                100.0,
                percentage,
            ),
        )

        with self.state.lock:

            self.state.battery = (
                percentage
            )

        return True

    # ========================================================
    # SET GPS
    # ========================================================

    def set_gps(
        self,
        fix_type=None,
        satellites=None,
        hdop=None,
        vdop=None,
    ) -> bool:

        with self.state.lock:

            if fix_type is not None:

                try:

                    fix_type = int(
                        fix_type
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

                self.state.gps_fix = max(
                    0,
                    min(
                        6,
                        fix_type,
                    ),
                )

            if satellites is not None:

                try:

                    satellites = int(
                        satellites
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

                self.state.satellites = max(
                    0,
                    min(
                        255,
                        satellites,
                    ),
                )

            if hdop is not None:

                try:

                    hdop = float(
                        hdop
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

                self.state.gps_hdop = max(
                    0.0,
                    hdop,
                )

            if vdop is not None:

                try:

                    vdop = float(
                        vdop
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    return False

                self.state.gps_vdop = max(
                    0.0,
                    vdop,
                )

        return True

    # ========================================================
    # ADD WAYPOINT
    #
    # Used by MissionReceiver.
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

        return self.mission.add_waypoint(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            speed=speed,
            hold_time=hold_time,
            name=name,
        )

    # ========================================================
    # CLEAR MISSION
    # ========================================================

    def clear_mission(
        self,
    ) -> bool:

        with self.state.lock:

            self.mission_navigator.reset()

            self.mission.clear()

            if not self.rtl_active:

                self.navigation.clear_target()

            self.flight_mode = (
                FlightMode.FREE
            )

            if self.state.airborne:

                self.state.mode = "HOLD"

            else:

                self.state.mode = "STANDBY"

        return True

    # ========================================================
    # START MISSION
    # ========================================================

    def start_mission(
        self,
    ) -> bool:

        if not self.state.armed:

            return False

        if self.mission.count() <= 0:

            return False

        with self.state.lock:

            # ------------------------------------------------
            # Cancel RTL
            # ------------------------------------------------

            self.rtl_active = False

            # ------------------------------------------------
            # Start navigator
            # ------------------------------------------------

            started = (
                self.mission_navigator.start()
            )

            if not started:

                return False

            self.flight_mode = (
                FlightMode.MISSION
            )

            self.state.mode = "AUTO"

            self.state.airborne = True

        return True

    # ========================================================
    # STOP MISSION
    # ========================================================

    def stop_mission(
        self,
    ) -> bool:

        with self.state.lock:

            self.mission_navigator.stop()

            self.flight_mode = (
                FlightMode.ALT_HOLD
            )

            self.flight_model.set_target_speed(
                0.0
            )

            self.flight_model.set_target_altitude(
                self.state.alt
            )

            self.navigation.clear_target()

            self.state.mode = "HOLD"

        return True

    # ========================================================
    # SET HOME = CURRENT POSITION
    #
    # home_lat/lon/alt are otherwise only set once, from the
    # DRONE CONFIGURATION panel values at Drone construction —
    # this lets the user re-anchor RTL's target to wherever the
    # drone currently is, without stopping/restarting the sim.
    # ========================================================

    def set_home_here(
        self,
    ) -> bool:

        with self.state.lock:

            self.home_lat = self.state.lat

            self.home_lon = self.state.lon

            self.home_alt = self.state.alt

        return True

    # ========================================================
    # RTL
    # ========================================================

    def rtl(
        self,
    ) -> bool:

        if not self.state.armed:

            return False

        with self.state.lock:

            # ------------------------------------------------
            # Stop mission
            # ------------------------------------------------

            self.mission_navigator.stop()

            # ------------------------------------------------
            # Hand horizontal control back from a lingering
            # joystick body_control_active (e.g. flown in FREE
            # mode just before hitting RTL) — otherwise it fully
            # overrides this RTL's target_speed/heading the
            # instant the next flight_model.update() runs.
            # ------------------------------------------------

            self.flight_model.release_body_velocity()

            # ------------------------------------------------
            # Enable RTL
            # ------------------------------------------------

            self.rtl_active = True

            # ------------------------------------------------
            # Home target
            # ------------------------------------------------

            self.navigation.set_target(
                lat=self.home_lat,
                lon=self.home_lon,
                alt=self.home_alt,
            )

            # ------------------------------------------------
            # RTL horizontal speed
            # ------------------------------------------------

            self.flight_model.set_target_speed(
                5.0
            )

            # ------------------------------------------------
            # Maintain current altitude during return
            # ------------------------------------------------

            self.flight_model.set_target_altitude(
                self.state.alt
            )

            self.state.mode = "RTL"

            self.flight_mode = (
                FlightMode.FREE
            )

            self.state.airborne = (
                self.state.alt > 0.01
            )

        return True

    # ========================================================
    # UPDATE RTL
    # ========================================================

    def _update_rtl(self):

        if not self.rtl_active:

            return

        # navigation.current_position is otherwise only kept
        # up to date by MissionNavigator (during an active
        # MISSION). RTL uses the same shared Navigation object
        # but never refreshed it, so bearing/distance were
        # computed against a stale (or, if no mission had ever
        # run, default 0,0) position — sending RTL off in the
        # wrong direction. Update it here every tick instead.

        self.navigation.set_current_position(
            lat=self.state.lat,
            lon=self.state.lon,
            alt=self.state.alt,
        )

        result = (
            self.navigation
            .get_navigation_result()
        )

        if result is None:

            return

        # ----------------------------------------------------
        # Returning to Home
        # ----------------------------------------------------

        # Once RTL is inside the horizontal arrival radius,
        # lock the simulated GPS position exactly to HOME.
        # Without this final capture, the 20 Hz integrator can
        # leave the aircraft a few metres beside HOME because
        # the commanded speed is reduced to zero over several
        # frames. A real autopilot also considers this an
        # arrival/position-hold condition rather than continuing
        # to integrate a stale horizontal velocity.
        if result.distance_m <= max(
            self.navigation.arrival_radius_m,
            0.5,
        ):

            self.state.lat = self.home_lat
            self.state.lon = self.home_lon

            self.flight_model.set_target_speed(
                0.0
            )

            self.flight_model.ground_speed = 0.0

            self.state.ground_speed = 0.0

            self.state.north_speed = 0.0
            self.state.east_speed = 0.0

            # Force navigation to see the exact HOME coordinate
            # before switching to the vertical descent phase.
            self.navigation.set_current_position(
                lat=self.home_lat,
                lon=self.home_lon,
                alt=self.state.alt,
            )

            result = self.navigation.get_navigation_result()

        if result.distance_m > (
            self.navigation.arrival_radius_m
        ):

            self.flight_model.set_target_heading(
                result.bearing_deg
            )

            # Slow down as the drone nears home instead of
            # cruising at full speed right up to arrival_radius_m
            # and then snapping to a stop.

            rtl_cruise_speed = 5.0

            deceleration_distance_m = 15.0

            if result.distance_m < deceleration_distance_m:

                speed_fraction = (
                    (
                        result.distance_m
                        - self.navigation.arrival_radius_m
                    )
                    / (
                        deceleration_distance_m
                        - self.navigation.arrival_radius_m
                    )
                )

                speed_fraction = max(
                    0.0,
                    min(
                        1.0,
                        speed_fraction,
                    ),
                )

                rtl_speed = (
                    rtl_cruise_speed * speed_fraction
                )

            else:

                rtl_speed = rtl_cruise_speed

            self.flight_model.set_target_speed(
                rtl_speed
            )

            # Hold cruise altitude while flying back; only
            # descend after arriving horizontally over home.

            self.flight_model.set_target_altitude(
                self.state.alt
            )

            return

        # ----------------------------------------------------
        # Arrived horizontally
        # ----------------------------------------------------

        self.flight_model.set_target_speed(
            0.0
        )

        # Arrived over home: descend straight to the ground
        # (0m) right away instead of home_alt, which is just
        # the altitude the drone happened to be armed at.

        self.flight_model.set_target_altitude(
            0.0
        )

        self.state.mode = "LAND"

        # ----------------------------------------------------
        # Check altitude
        # ----------------------------------------------------

        altitude_error = abs(
            self.state.alt
        )

        if (
            altitude_error
            <= self.navigation.altitude_tolerance_m
        ):

            self.flight_model.set_target_speed(
                0.0
            )

            self.flight_model.set_target_altitude(
                0.0
            )

            self.rtl_active = False

            self.navigation.clear_target()

            self.state.mode = "HOLD"

            self.flight_mode = (
                FlightMode.ALT_HOLD
            )

    # ========================================================
    # UPDATE MISSION
    # ========================================================

    def _update_mission(self):

        waypoint = (
            self.mission_navigator.update(
                lat=self.state.lat,
                lon=self.state.lon,
                alt=self.state.alt,
                sim_time=self.state.sim_time,
            )
        )

        # ----------------------------------------------------
        # Mission completed
        # ----------------------------------------------------

        if (
            waypoint is None
            and
            self.mission_navigator.is_completed()
        ):

            self.flight_model.set_target_speed(
                0.0
            )

            self.flight_model.set_target_altitude(
                self.state.alt
            )

            self.navigation.clear_target()

            self.state.mode = "HOLD"

            return

        # ----------------------------------------------------
        # No active waypoint
        # ----------------------------------------------------

        if waypoint is None:

            return

        # ----------------------------------------------------
        # Navigation result
        # ----------------------------------------------------

        result = (
            self.mission_navigator
            .get_navigation_result()
        )

        if result is None:

            return

        # ----------------------------------------------------
        # Holding at this waypoint (e.g. a DELAY item counting
        # down): sit still instead of chasing a bearing that's
        # jittery this close to the target, which was making
        # the drone circle in place instead of stopping.
        # ----------------------------------------------------

        if self.mission_navigator.is_holding():

            self.flight_model.set_target_speed(
                0.0
            )

            self.flight_model.set_target_altitude(
                waypoint.altitude
            )

            return

        # ----------------------------------------------------
        # Heading
        # ----------------------------------------------------

        self.flight_model.set_target_heading(
            result.bearing_deg
        )

        # ----------------------------------------------------
        # Speed from WP
        # ----------------------------------------------------

        self.flight_model.set_target_speed(
            waypoint.speed
        )

        # ----------------------------------------------------
        # Altitude from WP
        # ----------------------------------------------------

        self.flight_model.set_target_altitude(
            waypoint.altitude
        )

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        dt,
    ):

        if dt <= 0.0:

            return

        with self.state.lock:

            self.state.sim_time += dt

            # =================================================
            # RTL
            # =================================================

            if self.rtl_active:

                self._update_rtl()

            # =================================================
            # MISSION
            # =================================================

            elif (
                self.flight_mode
                == FlightMode.MISSION
            ):

                if (
                    self.mission_navigator
                    .is_active()
                ):

                    self._update_mission()

            # =================================================
            # ALT HOLD
            # =================================================

            elif (
                self.flight_mode
                == FlightMode.ALT_HOLD
            ):

                # FlightModel continuously tracks
                # target_altitude.
                pass

            # =================================================
            # FREE
            # =================================================

            elif (
                self.flight_mode
                == FlightMode.FREE
            ):

                # Runtime control changes FlightModel targets.
                pass

            # =================================================
            # FLIGHT MODEL
            # =================================================

            self.flight_model.update(
                self.state,
                dt,
            )

            # =================================================
            # BATTERY
            # =================================================

            self._update_battery(
                dt
            )

            # =================================================
            # GROUND
            # =================================================

            if (
                self.state.alt <= 0.01
                and
                self.flight_model.target_altitude
                <= 0.0
            ):

                self.state.alt = 0.0

                self.state.vertical_speed = 0.0

                self.state.airborne = False

                self.flight_model.set_target_speed(
                    0.0
                )

                if self.state.mode in (
                    "LAND",
                    "RTL",
                ):

                    self.state.mode = "HOLD"

                    # Touching down from a commanded LAND/RTL
                    # disarms automatically, so the next flight
                    # requires an explicit ARM again.

                    self.state.armed = False

                if self.rtl_active:

                    self.rtl_active = False

                    self.navigation.clear_target()

    # ========================================================
    # BATTERY
    # ========================================================

    def _update_battery(
        self,
        dt,
    ):

        # ----------------------------------------------------
        # Base electronics consumption
        # ----------------------------------------------------

        base_consumption = 0.002

        # ----------------------------------------------------
        # Additional flight consumption
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Approximate voltage
        # ----------------------------------------------------

        self.state.voltage = (
            14.0
            +
            (
                self.state.battery
                / 100.0
            )
            * 2.8
        )

        # ----------------------------------------------------
        # Approximate current
        # ----------------------------------------------------

        self.state.current = (
            2.0
            +
            self.state.ground_speed
            * 0.3
        )

    # ========================================================
    # HOME
    # ========================================================

    def get_home_position(
        self,
    ):

        return {
            "lat": self.home_lat,
            "lon": self.home_lon,
            "alt": self.home_alt,
        }

    # ========================================================
    # MISSION STATUS
    # ========================================================

    def get_current_waypoint(
        self,
    ):

        return (
            self.mission_navigator
            .get_current_waypoint()
        )

    # ========================================================

    def is_mission_active(
        self,
    ):

        return (
            self.mission_navigator
            .is_active()
        )

    # ========================================================

    def is_mission_completed(
        self,
    ):

        return (
            self.mission_navigator
            .is_completed()
        )

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(
        self,
    ):

        status = (
            self.state.get_status()
        )

        waypoint = (
            self.get_current_waypoint()
        )

        navigation = (
            self.mission_navigator
            .get_navigation_result()
        )

        # ----------------------------------------------------
        # RTL navigation
        # ----------------------------------------------------

        rtl_navigation = None

        if self.rtl_active:

            rtl_navigation = (
                self.navigation
                .get_navigation_result()
            )

        active_navigation = (
            rtl_navigation
            if rtl_navigation is not None
            else navigation
        )

        # ----------------------------------------------------
        # Target values
        # ----------------------------------------------------

        if waypoint is not None:

            target_lat = (
                waypoint.latitude
            )

            target_lon = (
                waypoint.longitude
            )

            target_alt = (
                waypoint.altitude
            )

            target_speed = (
                waypoint.speed
            )

        elif self.rtl_active:

            target_lat = self.home_lat

            target_lon = self.home_lon

            target_alt = self.home_alt

            target_speed = 5.0

        else:

            target_lat = None

            target_lon = None

            target_alt = (
                self.flight_model
                .target_altitude
            )

            target_speed = (
                self.flight_model
                .target_speed
            )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        status.update({

            # =================================================
            # MODE
            # =================================================

            "flight_mode":
                self.get_mode(),

            # =================================================
            # MISSION
            # =================================================

            "mission_active":
                self.is_mission_active(),

            "mission_completed":
                self.is_mission_completed(),

            "mission_count":
                self.mission.count(),

            "current_waypoint":
                waypoint.index
                if waypoint is not None
                else None,

            # =================================================
            # TARGET
            # =================================================

            "target_lat":
                target_lat,

            "target_lon":
                target_lon,

            "target_alt":
                target_alt,

            "target_speed":
                target_speed,

            # =================================================
            # NAVIGATION
            # =================================================

            "distance_to_target":
                active_navigation.distance_m
                if active_navigation is not None
                else None,

            "bearing_to_target":
                active_navigation.bearing_deg
                if active_navigation is not None
                else None,

            "altitude_error":
                active_navigation.altitude_error_m
                if active_navigation is not None
                else (
                    self.flight_model
                    .target_altitude
                    - self.state.alt
                ),

            # =================================================
            # RTL
            # =================================================

            "rtl_active":
                self.rtl_active,

            # =================================================
            # HOME
            # =================================================

            "home_lat":
                self.home_lat,

            "home_lon":
                self.home_lon,

            "home_alt":
                self.home_alt,

            # =================================================
            # FLIGHT MODEL TARGET
            # =================================================

            "target_altitude":
                self.flight_model
                .target_altitude,

            "target_ground_speed":
                self.flight_model
                .target_speed,

            "target_heading":
                self.flight_model
                .target_heading,

            # =================================================
            # ATTITUDE TARGET/STATE
            # =================================================

            "roll":
                getattr(
                    self.state,
                    "roll",
                    0.0,
                ),

            "pitch":
                getattr(
                    self.state,
                    "pitch",
                    0.0,
                ),

            "yaw":
                getattr(
                    self.state,
                    "yaw",
                    0.0,
                ),

            # =================================================
            # GPS
            # =================================================

            "gps_fix":
                getattr(
                    self.state,
                    "gps_fix",
                    3,
                ),

            "satellites":
                getattr(
                    self.state,
                    "satellites",
                    12,
                ),

            "gps_hdop":
                getattr(
                    self.state,
                    "gps_hdop",
                    1.0,
                ),

            "gps_vdop":
                getattr(
                    self.state,
                    "gps_vdop",
                    1.0,
                ),

            # =================================================
            # BATTERY
            # =================================================

            "battery":
                getattr(
                    self.state,
                    "battery",
                    100.0,
                ),

            "voltage":
                getattr(
                    self.state,
                    "voltage",
                    16.8,
                ),

            "current":
                getattr(
                    self.state,
                    "current",
                    0.0,
                ),
        })

        return status