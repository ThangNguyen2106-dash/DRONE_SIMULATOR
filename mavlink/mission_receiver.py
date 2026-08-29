"""
MAVLink mission receiver.

Handles MAVLink mission upload/download between
Ground Control Station and the simulated drone.

Supported:

    UPLOAD
        MISSION_COUNT
        MISSION_ITEM_INT
        MISSION_ITEM

    DOWNLOAD
        MISSION_REQUEST_LIST
        MISSION_REQUEST_INT
        MISSION_REQUEST

    CONTROL
        MISSION_CLEAR_ALL
        MISSION_SET_CURRENT

The important implementation detail in this project is:

    MAVLink message
          |
          | *_encode()
          v
    MAVLink message object
          |
          | connection.send()
          v
    UDP socket

Do NOT call pymavlink *_send() functions directly because
the project's MAVLink object is created as MAVLink(None).
"""


from pymavlink import mavutil

from simulator.mission import Mission
from .mav_logger import mav_log, MISSION, TX, RX


# ============================================================
# MISSION RECEIVER
# ============================================================

class MissionReceiver:

    def __init__(
        self,
        connection,
        mission: Mission,
        system_id: int,
        component_id: int,
        get_home_position=None,
    ):

        self.connection = connection

        self.mission = mission

        self.system_id = int(
            system_id
        )

        self.component_id = int(
            component_id
        )

        # Callable returning {"lat", "lon", "alt"} for the
        # drone's home position, used to resolve
        # MAV_CMD_NAV_RETURN_TO_LAUNCH mission items.
        self.get_home_position = get_home_position

        # ====================================================
        # UPLOAD STATE
        # ====================================================

        self.upload_active = False

        self.expected_count = 0

        self.expected_seq = 0

        self.received_count = 0

        # Mission-level speed command (MAV_CMD_DO_CHANGE_SPEED).
        self.pending_speed = 5.0

        # ====================================================
        # STAGING MISSION
        # ====================================================

        self.staging_mission = Mission()

        # ====================================================
        # DOWNLOAD STATE
        # ====================================================

        self.download_active = False

        self.download_index = 0

        # ====================================================
        # GCS SOURCE
        # ====================================================

        self.sender_system = None

        self.sender_component = None

    # ========================================================
    # PROCESS MESSAGE
    # ========================================================

    def process(
        self,
        message,
    ) -> bool:

        if message is None:

            return False

        try:

            message_type = (
                message.get_type()
            )

        except Exception:

            return False

        # ====================================================
        # UPLOAD
        # ====================================================

        if message_type == "MISSION_COUNT":

            self._handle_mission_count(
                message
            )

            return True

        if message_type == "MISSION_ITEM_INT":

            self._handle_mission_item_int(
                message
            )

            return True

        if message_type == "MISSION_ITEM":

            self._handle_mission_item(
                message
            )

            return True

        # ====================================================
        # CLEAR
        # ====================================================

        if message_type == "MISSION_CLEAR_ALL":

            self._handle_clear_all(
                message
            )

            return True

        # ====================================================
        # DOWNLOAD
        # ====================================================

        if message_type == "MISSION_REQUEST_LIST":

            self._handle_request_list(
                message
            )

            return True

        if message_type == "MISSION_REQUEST_INT":

            self._handle_request_int(
                message
            )

            return True

        if message_type == "MISSION_REQUEST":

            self._handle_request(
                message
            )

            return True

        # ====================================================
        # SET CURRENT
        # ====================================================

        if message_type == "MISSION_SET_CURRENT":

            self._handle_set_current(
                message
            )

            return True

        return False

    # ========================================================
    # SOURCE
    # ========================================================

    def _remember_sender(
        self,
        message,
    ):

        try:

            self.sender_system = int(
                message.get_srcSystem()
            )

        except Exception:

            pass

        try:

            self.sender_component = int(
                message.get_srcComponent()
            )

        except Exception:

            pass

    # ========================================================
    # TARGET
    # ========================================================

    def _target_system(
        self,
    ) -> int:

        if self.sender_system is None:

            return 0

        return int(
            self.sender_system
        )

    # ========================================================

    def _target_component(
        self,
    ) -> int:

        if self.sender_component is None:

            return 0

        return int(
            self.sender_component
        )

    # ========================================================
    # GET MAVLINK ENCODER
    # ========================================================

    def _get_mavlink(
        self,
    ):

        if self.connection is None:

            return None

        return getattr(
            self.connection,
            "mavlink",
            None,
        )

    # ========================================================
    # SEND ENCODED MESSAGE
    # ========================================================

    def _send_message(
        self,
        message,
        description="",
    ) -> bool:
        """
        Send an already encoded MAVLink message
        through the project's MAVLinkConnection.
        """

        if message is None:

            return False

        if self.connection is None:

            return False

        try:

            result = self.connection.send(
                message
            )

        except Exception as exc:

            mav_log.error(TX, f"{description}: {type(exc).__name__}: {exc}")

            return False

        if not result:

            mav_log.warn(TX, f"send failed: {description}")

            return False

        mav_log.debug(TX, description)

        return True

    # ========================================================
    # MISSION COUNT
    # ========================================================

    def _handle_mission_count(
        self,
        message,
    ):

        self._remember_sender(
            message
        )

        try:

            count = int(
                message.count
            )

        except Exception:

            self._send_mission_ack(
                mavutil.mavlink.MAV_MISSION_ERROR
            )

            return

        mav_log.info(RX, f"MISSION_COUNT={count}")

        # ====================================================
        # EMPTY MISSION
        # ====================================================

        if count <= 0:

            self.upload_active = False

            self.expected_count = 0

            self.expected_seq = 0

            self.received_count = 0

            self.staging_mission.clear()

            self.mission.clear()

            self._send_mission_ack(
                mavutil.mavlink.MAV_MISSION_ACCEPTED
            )

            mav_log.info(MISSION, "Empty mission accepted")

            return

        # ====================================================
        # SAFETY LIMIT
        # ====================================================

        if count > 1000:

            self._send_mission_ack(
                mavutil.mavlink.MAV_MISSION_ERROR
            )

            mav_log.warn(MISSION, f"Mission rejected: too many items ({count})")

            return

        # ====================================================
        # START STAGING
        # ====================================================

        self.staging_mission.clear()

        self.upload_active = True

        self.expected_count = count

        self.expected_seq = 0

        self.received_count = 0

        self.pending_speed = 5.0

        # New upload invalidates any download.

        self.download_active = False

        self.download_index = 0

        # ====================================================
        # REQUEST FIRST ITEM
        # ====================================================

        self._request_item(
            0
        )

    # ========================================================
    # MISSION ITEM INT
    # ========================================================

    def _handle_mission_item_int(
        self,
        message,
    ):

        if not self.upload_active:

            mav_log.warn(RX, "Unexpected MISSION_ITEM_INT")

            return

        self._remember_sender(
            message
        )

        try:

            seq = int(
                message.seq
            )

        except Exception:

            mav_log.warn(RX, "Invalid MISSION_ITEM_INT seq")

            return

        # ====================================================
        # SEQUENCE
        # ====================================================

        if seq != self.expected_seq:

            mav_log.warn(RX, f"Unexpected seq={seq}, expected={self.expected_seq}")

            self._request_item(
                self.expected_seq
            )

            return

        # ====================================================
        # STORE
        # ====================================================

        accepted = (
            self._store_mission_item_int(
                message
            )
        )

        if not accepted:

            self._send_mission_ack(
                mavutil.mavlink.MAV_MISSION_UNSUPPORTED
            )

            self.upload_active = False

            self.staging_mission.clear()

            return

        self.received_count += 1

        self.expected_seq += 1

        # ====================================================
        # COMPLETE
        # ====================================================

        if (
            self.received_count
            >= self.expected_count
        ):

            self._finish_upload()

            return

        # ====================================================
        # REQUEST NEXT
        # ====================================================

        self._request_item(
            self.expected_seq
        )

    # ========================================================
    # MISSION ITEM LEGACY
    # ========================================================

    def _handle_mission_item(
        self,
        message,
    ):

        if not self.upload_active:

            mav_log.warn(RX, "Unexpected MISSION_ITEM")

            return

        self._remember_sender(
            message
        )

        try:

            seq = int(
                message.seq
            )

        except Exception:

            mav_log.warn(RX, "Invalid MISSION_ITEM seq")

            return

        # ====================================================
        # SEQUENCE
        # ====================================================

        if seq != self.expected_seq:

            self._request_item(
                self.expected_seq
            )

            return

        # ====================================================
        # STORE
        # ====================================================

        accepted = (
            self._store_mission_item_legacy(
                message
            )
        )

        if not accepted:

            self._send_mission_ack(
                mavutil.mavlink.MAV_MISSION_UNSUPPORTED
            )

            self.upload_active = False

            self.staging_mission.clear()

            return

        self.received_count += 1

        self.expected_seq += 1

        # ====================================================
        # COMPLETE
        # ====================================================

        if (
            self.received_count
            >= self.expected_count
        ):

            self._finish_upload()

            return

        # ====================================================
        # NEXT
        # ====================================================

        self._request_item(
            self.expected_seq
        )

    # ========================================================
    # COMMAND SETS
    #
    # NAV_POSITION_COMMANDS carry a real lat/lon/alt target and
    # get inserted as a flyable Waypoint. NOOP_COMMANDS are
    # accessory DO_*/CONDITION_* items Mission Planner may add
    # to a mission (camera, servo, ROI, jump, fencing, ...) that
    # this simulator has no physical model for — they're ACKed
    # as accepted (so the whole mission still uploads) but don't
    # produce a waypoint or affect navigation.
    # ========================================================

    @staticmethod
    def _nav_position_commands():

        mav = mavutil.mavlink

        return {
            mav.MAV_CMD_NAV_WAYPOINT,
            mav.MAV_CMD_NAV_TAKEOFF,
            mav.MAV_CMD_NAV_LAND,
            mav.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            getattr(mav, "MAV_CMD_NAV_SPLINE_WAYPOINT", 82),
            getattr(mav, "MAV_CMD_NAV_LOITER_UNLIM", 17),
            getattr(mav, "MAV_CMD_NAV_LOITER_TURNS", 18),
            getattr(mav, "MAV_CMD_NAV_LOITER_TIME", 19),
            getattr(mav, "MAV_CMD_NAV_DELAY", 93),
            getattr(mav, "MAV_CMD_CONDITION_DELAY", 112),
        }

    @staticmethod
    def _noop_commands():

        mav = mavutil.mavlink

        return {
            getattr(mav, "MAV_CMD_CONDITION_YAW", 115),
            getattr(mav, "MAV_CMD_DO_JUMP", 177),
            getattr(mav, "MAV_CMD_DO_SET_HOME", 179),
            getattr(mav, "MAV_CMD_DO_SET_RELAY", 181),
            getattr(mav, "MAV_CMD_DO_REPEAT_RELAY", 182),
            getattr(mav, "MAV_CMD_DO_SET_SERVO", 183),
            getattr(mav, "MAV_CMD_DO_REPEAT_SERVO", 184),
            getattr(mav, "MAV_CMD_DO_LAND_START", 189),
            getattr(mav, "MAV_CMD_DO_FENCE_ENABLE", 207),
            getattr(mav, "MAV_CMD_DO_PARACHUTE", 208),
            getattr(mav, "MAV_CMD_DO_INVERTED_FLIGHT", 210),
            getattr(mav, "MAV_CMD_DO_GRIPPER", 211),
            getattr(mav, "MAV_CMD_DO_GUIDED_LIMITS", 222),
            getattr(mav, "MAV_CMD_DO_ENGINE_CONTROL", 223),
            getattr(mav, "MAV_CMD_DO_SET_ROI", 201),
            getattr(mav, "MAV_CMD_DO_SET_ROI_LOCATION", 195),
            getattr(mav, "MAV_CMD_DO_SET_ROI_NONE", 197),
            getattr(mav, "MAV_CMD_DO_DIGICAM_CONFIGURE", 202),
            getattr(mav, "MAV_CMD_DO_DIGICAM_CONTROL", 203),
            getattr(mav, "MAV_CMD_DO_MOUNT_CONTROL", 205),
            getattr(mav, "MAV_CMD_DO_SET_CAM_TRIGG_DIST", 206),
            getattr(mav, "MAV_CMD_DO_VTOL_TRANSITION", 3000),
            getattr(mav, "MAV_CMD_DO_AUTOTUNE_ENABLE", 211),
        }

    # ========================================================
    # ACTION FOR COMMAND
    #
    # Maps a MAV_CMD to the Waypoint.action label so the GUI
    # mission table can show what each step actually does
    # (TAKEOFF / LAND / DELAY / RTL / WAYPOINT) instead of
    # lumping every non-RTL item together as a plain waypoint.
    # ========================================================

    @staticmethod
    def _action_for_command(command) -> str:

        if command == mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH:

            return "rtl"

        if command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:

            return "takeoff"

        if command == mavutil.mavlink.MAV_CMD_NAV_LAND:

            return "land"

        if command == getattr(
            mavutil.mavlink, "MAV_CMD_NAV_LOITER_TIME", 19
        ):

            # Loiter-for-a-duration at the current waypoint —
            # the closest MAVLink equivalent to a plain "delay".
            return "loiter"

        if command in (
            getattr(mavutil.mavlink, "MAV_CMD_NAV_DELAY", 93),
            getattr(mavutil.mavlink, "MAV_CMD_CONDITION_DELAY", 112),
        ):

            return "delay"

        return "waypoint"

    # ========================================================
    # STORE INT ITEM
    # ========================================================

    def _store_mission_item_int(
        self,
        message,
    ) -> bool:

        try:

            command = int(
                message.command
            )

            sequence = int(
                message.seq
            )

        except Exception:

            return False

        # ====================================================
        # MISSION COMMANDS
        # ====================================================

        change_speed_command = getattr(
            mavutil.mavlink, "MAV_CMD_DO_CHANGE_SPEED", 178
        )

        if command == change_speed_command:
            try:
                # param2 = speed in m/s for MAV_CMD_DO_CHANGE_SPEED.
                self.pending_speed = max(0.0, float(message.param2))
            except Exception:
                return False
            mav_log.info(RX, f"DO_CHANGE_SPEED -> {self.pending_speed:.2f} m/s")
            return True

        if command in self._noop_commands():

            mav_log.info(RX, f"Accepted no-op command={command}")

            return True

        delay_commands = {
            getattr(mavutil.mavlink, "MAV_CMD_NAV_DELAY", 93),
            getattr(mavutil.mavlink, "MAV_CMD_CONDITION_DELAY", 112),
        }

        supported_commands = self._nav_position_commands()

        if command not in supported_commands:

            mav_log.warn(RX, f"Unsupported command={command}")

            return False

        # ====================================================
        # RETURN TO LAUNCH
        #
        # GCS usually sends x=y=z=0 for this item. The real
        # target is the drone's home position.
        # ====================================================

        is_rtl = (
            command
            == mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH
        )

        is_delay = command in delay_commands

        if is_rtl:

            home = self._resolve_home()

            if home is None:

                return False

            latitude = home["lat"]

            longitude = home["lon"]

            altitude = home["alt"]

        elif is_delay:

            position = self._resolve_delay_position()

            if position is None:

                return False

            latitude = position["lat"]

            longitude = position["lon"]

            altitude = position["alt"]

        else:

            # ================================================
            # GPS
            # ================================================

            try:

                latitude = (
                    float(message.x)
                    / 10_000_000.0
                )

                longitude = (
                    float(message.y)
                    / 10_000_000.0
                )

                altitude = (
                    self._resolve_altitude(
                        message
                    )
                )

            except Exception:

                return False

            # ================================================
            # COORDINATE VALIDATION
            # ================================================

            if not (
                -90.0
                <= latitude
                <= 90.0
            ):

                return False

            if not (
                -180.0
                <= longitude
                <= 180.0
            ):

                return False

        # ====================================================
        # HOLD TIME
        # ====================================================

        hold_time = 0.0

        try:

            hold_time = max(
                0.0,
                float(
                    message.param1
                ),
            )

        except Exception:

            pass

        # ====================================================
        # ACCEPTANCE RADIUS
        # ====================================================

        acceptance_radius = None

        try:

            acceptance_radius = max(
                0.0,
                float(
                    message.param2
                ),
            )

        except Exception:

            pass

        # ====================================================
        # YAW
        # ====================================================

        yaw = None

        try:

            yaw = float(
                message.param4
            )

        except Exception:

            pass

        # ====================================================
        # SPEED
        # ====================================================

        # Mission protocol itself does not contain a simple
        # per-WP speed field in MISSION_ITEM_INT.
        #
        # The simulator therefore uses 5 m/s as the default.
        #

        speed = max(0.0, float(self.pending_speed))

        # ====================================================
        # ADD WAYPOINT
        # ====================================================

        waypoint = (
            self.staging_mission
            .add_waypoint(
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                speed=speed,
                hold_time=hold_time,
                name=(
                    "RTL"
                    if is_rtl
                    else "DELAY"
                    if is_delay
                    else f"WP{sequence + 1}"
                ),
                action=self._action_for_command(
                    command
                ),
                command=command,
                acceptance_radius=acceptance_radius or 0.0,
                yaw=yaw or 0.0,
            )
        )

        # Preserve the original MAVLink sequence.
        waypoint.source_seq = sequence

        # Store extra values when the waypoint object supports
        # them. This keeps compatibility with the existing
        # Mission implementation.

        if acceptance_radius is not None:

            try:

                waypoint.acceptance_radius = (
                    acceptance_radius
                )

            except Exception:

                pass

        if yaw is not None:

            try:

                waypoint.yaw = yaw

            except Exception:

                pass

        mav_log.info(
            RX,
            f"{waypoint.name}: LAT={latitude:.7f} LON={longitude:.7f} "
            f"ALT={altitude:.2f} HOLD={hold_time:.1f}s",
        )

        return True

    # ========================================================
    # STORE LEGACY ITEM
    # ========================================================

    def _store_mission_item_legacy(
        self,
        message,
    ) -> bool:

        try:

            command = int(
                message.command
            )

            sequence = int(
                message.seq
            )

            latitude = float(
                message.x
            )

            longitude = float(
                message.y
            )

            altitude = float(
                message.z
            )

        except Exception:

            return False

        # ====================================================
        # COMMAND
        # ====================================================

        change_speed_command = getattr(
            mavutil.mavlink, "MAV_CMD_DO_CHANGE_SPEED", 178
        )

        if command == change_speed_command:
            try:
                self.pending_speed = max(0.0, float(message.param2))
            except Exception:
                return False
            mav_log.info(RX, f"DO_CHANGE_SPEED -> {self.pending_speed:.2f} m/s")
            return True

        if command in self._noop_commands():

            mav_log.info(RX, f"Accepted no-op command={command}")

            return True

        delay_commands = {
            getattr(mavutil.mavlink, "MAV_CMD_NAV_DELAY", 93),
            getattr(mavutil.mavlink, "MAV_CMD_CONDITION_DELAY", 112),
        }

        supported_commands = self._nav_position_commands()

        if command not in supported_commands:

            mav_log.warn(RX, f"Unsupported command={command}")

            return False

        is_rtl = (
            command
            == mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH
        )

        is_delay = command in delay_commands

        if is_rtl:

            home = self._resolve_home()

            if home is None:

                return False

            latitude = home["lat"]

            longitude = home["lon"]

            altitude = home["alt"]

        elif is_delay:

            position = self._resolve_delay_position()

            if position is None:

                return False

            latitude = position["lat"]

            longitude = position["lon"]

            altitude = position["alt"]

        else:

            # ================================================
            # VALIDATION
            # ================================================

            if not (
                -90.0
                <= latitude
                <= 90.0
            ):

                return False

            if not (
                -180.0
                <= longitude
                <= 180.0
            ):

                return False

        # ====================================================
        # HOLD
        # ====================================================

        hold_time = 0.0

        try:

            hold_time = max(
                0.0,
                float(
                    message.param1
                ),
            )

        except Exception:

            pass

        # ====================================================
        # WAYPOINT
        # ====================================================

        waypoint = (
            self.staging_mission
            .add_waypoint(
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                speed=max(0.0, float(self.pending_speed)),
                hold_time=hold_time,
                name=(
                    "RTL"
                    if is_rtl
                    else "DELAY"
                    if is_delay
                    else f"WP{sequence + 1}"
                ),
                action=self._action_for_command(
                    command
                ),
                command=command,
                acceptance_radius=max(0.0, float(getattr(message, "param2", 0.0))),
                yaw=float(getattr(message, "param4", 0.0)),
            )
        )

        waypoint.source_seq = sequence

        mav_log.info(
            RX,
            f"{waypoint.name}: LAT={latitude:.7f} LON={longitude:.7f} "
            f"ALT={altitude:.2f} HOLD={hold_time:.1f}s",
        )

        return True

    # ========================================================
    # HOME
    # ========================================================

    def _resolve_home(
        self,
    ):

        if self.get_home_position is None:

            return None

        try:

            home = self.get_home_position()

            return {
                "lat": float(home["lat"]),
                "lon": float(home["lon"]),
                "alt": float(home["alt"]),
            }

        except Exception:

            return None

    # ========================================================
    # DELAY POSITION
    #
    # MAV_CMD_NAV_DELAY (and _CONDITION_DELAY) items don't carry
    # a real target — GCS tools like Mission Planner send x=y=z=0
    # since the drone should simply pause where it already is.
    # Anchor the delay to the previous waypoint's position (or
    # home, if this is the first item) so the mission doesn't
    # jump anywhere for it.
    # ========================================================

    def _resolve_delay_position(
        self,
    ):

        if self.staging_mission.waypoints:

            last = self.staging_mission.waypoints[-1]

            return {
                "lat": float(last.latitude),
                "lon": float(last.longitude),
                "alt": float(last.altitude),
            }

        return self._resolve_home()

    # ========================================================
    # ALTITUDE
    # ========================================================

    def _resolve_altitude(
        self,
        message,
    ) -> float:

        try:

            frame = int(
                message.frame
            )

        except Exception:

            frame = getattr(
                mavutil.mavlink,
                "MAV_FRAME_GLOBAL_RELATIVE_ALT_INT",
                6,
            )

        try:

            altitude = float(
                message.z
            )

        except Exception:

            return 0.0

        # ====================================================
        # RELATIVE ALTITUDE
        # ====================================================

        relative_frames = {

            getattr(
                mavutil.mavlink,
                "MAV_FRAME_GLOBAL_RELATIVE_ALT_INT",
                6,
            ),

            getattr(
                mavutil.mavlink,
                "MAV_FRAME_GLOBAL_RELATIVE_ALT",
                3,
            ),
        }

        # ====================================================
        # ABSOLUTE ALTITUDE
        # ====================================================

        absolute_frames = {

            getattr(
                mavutil.mavlink,
                "MAV_FRAME_GLOBAL_INT",
                5,
            ),

            getattr(
                mavutil.mavlink,
                "MAV_FRAME_GLOBAL",
                0,
            ),
        }

        if frame in relative_frames:

            return altitude

        if frame in absolute_frames:

            return altitude

        mav_log.warn(RX, f"Unknown frame={frame}; using z={altitude}")

        return altitude

    # ========================================================
    # REQUEST ITEM
    # ========================================================

    def _request_item(
        self,
        sequence: int,
    ) -> bool:
        """
        Ask GCS for one mission item.

        IMPORTANT:
        Uses mission_request_int_encode() followed by
        self.connection.send().
        """

        mav = self._get_mavlink()

        if mav is None:

            mav_log.error(TX, "MAVLink encoder unavailable")

            return False

        sequence = int(
            sequence
        )

        target_system = (
            self._target_system()
        )

        target_component = (
            self._target_component()
        )

        mission_type = getattr(
            mavutil.mavlink,
            "MAV_MISSION_TYPE_MISSION",
            0,
        )

        # ====================================================
        # ENCODE
        # ====================================================

        try:

            encoder = getattr(
                mav,
                "mission_request_int_encode",
                None,
            )

            if encoder is None:

                mav_log.error(TX, "mission_request_int_encode unavailable")

                return False

            try:

                message = encoder(
                    target_system,
                    target_component,
                    sequence,
                    mission_type,
                )

            except TypeError:

                message = encoder(
                    target_system,
                    target_component,
                    sequence,
                )

        except Exception as exc:

            mav_log.error(TX, f"MISSION_REQUEST_INT encode: {type(exc).__name__}: {exc}")

            return False

        # ====================================================
        # SEND
        # ====================================================

        return self._send_message(
            message,
            (
                "MISSION_REQUEST_INT "
                f"seq={sequence}"
            ),
        )

    # ========================================================
    # FINISH UPLOAD
    # ========================================================

    def _finish_upload(
        self,
    ):

        # ====================================================
        # REPLACE ACTIVE MISSION
        # ====================================================

        self.mission.clear()

        for waypoint in (
            self.staging_mission.get_all()
        ):

            new_waypoint = (
                self.mission.add_waypoint(
                    latitude=(
                        waypoint.latitude
                    ),
                    longitude=(
                        waypoint.longitude
                    ),
                    altitude=(
                        waypoint.altitude
                    ),
                    speed=(
                        waypoint.speed
                    ),
                    hold_time=(
                        waypoint.hold_time
                    ),
                    name=(
                        waypoint.name
                    ),
                )
            )

            # Preserve optional attributes.

            for attribute in (
                "acceptance_radius",
                "yaw",
                "command",
                "source_seq",
                "action",
            ):

                if hasattr(
                    waypoint,
                    attribute,
                ):

                    try:

                        setattr(
                            new_waypoint,
                            attribute,
                            getattr(
                                waypoint,
                                attribute,
                            ),
                        )

                    except Exception:

                        pass

        self.upload_active = False

        self.expected_count = (
            self.mission.count()
        )

        self.received_count = (
            self.mission.count()
        )

        self.expected_seq = (
            self.mission.count()
        )

        self.download_active = False

        self.download_index = 0

        mav_log.info(MISSION, f"Upload complete: {self.mission.count()} waypoints accepted")

        # ====================================================
        # ACK
        # ====================================================

        self._send_mission_ack(
            mavutil.mavlink.MAV_MISSION_ACCEPTED
        )

    # ========================================================
    # CLEAR ALL
    # ========================================================

    def _handle_clear_all(
        self,
        message,
    ):

        self._remember_sender(
            message
        )

        self.upload_active = False

        self.download_active = False

        self.expected_count = 0

        self.expected_seq = 0

        self.received_count = 0

        self.download_index = 0

        self.staging_mission.clear()

        self.mission.clear()

        mav_log.info(MISSION, "Mission cleared by GCS")

        self._send_mission_ack(
            mavutil.mavlink.MAV_MISSION_ACCEPTED
        )

    # ========================================================
    # REQUEST LIST
    # ========================================================

    def _handle_request_list(
        self,
        message,
    ):

        self._remember_sender(
            message
        )

        count = self.mission.count()

        mav_log.info(RX, f"MISSION_REQUEST_LIST count={count}")

        self.download_active = True

        self.download_index = 0

        self._send_mission_count(
            count
        )

    # ========================================================
    # REQUEST INT
    # ========================================================

    def _handle_request_int(
        self,
        message,
    ):

        self._remember_sender(
            message
        )

        try:

            sequence = int(
                message.seq
            )

        except Exception:

            return

        self._send_mission_item_int(
            sequence
        )

    # ========================================================
    # REQUEST LEGACY
    # ========================================================

    def _handle_request(
        self,
        message,
    ):

        self._remember_sender(
            message
        )

        try:

            sequence = int(
                message.seq
            )

        except Exception:

            return

        self._send_mission_item(
            sequence
        )

    # ========================================================
    # SEND MISSION COUNT
    # ========================================================

    def _send_mission_count(
        self,
        count: int,
    ) -> bool:

        mav = self._get_mavlink()

        if mav is None:

            return False

        target_system = (
            self._target_system()
        )

        target_component = (
            self._target_component()
        )

        count = int(
            count
        )

        mission_type = getattr(
            mavutil.mavlink,
            "MAV_MISSION_TYPE_MISSION",
            0,
        )

        try:

            encoder = getattr(
                mav,
                "mission_count_encode",
                None,
            )

            if encoder is None:

                return False

            try:

                message = encoder(
                    target_system,
                    target_component,
                    count,
                    mission_type,
                )

            except TypeError:

                message = encoder(
                    target_system,
                    target_component,
                    count,
                )

        except Exception as exc:

            mav_log.error(TX, f"MISSION_COUNT encode: {type(exc).__name__}: {exc}")

            return False

        return self._send_message(
            message,
            f"MISSION_COUNT={count}",
        )

    # ========================================================
    # SEND MISSION ITEM INT
    # ========================================================

    def _send_mission_item_int(
        self,
        sequence: int,
    ) -> bool:

        mav = self._get_mavlink()

        if mav is None:

            return False

        sequence = int(
            sequence
        )

        waypoint = (
            self.mission.get_waypoint(
                sequence + 1
            )
        )

        if waypoint is None:

            mav_log.warn(TX, f"Waypoint seq={sequence} does not exist")

            return False

        target_system = (
            self._target_system()
        )

        target_component = (
            self._target_component()
        )

        frame = getattr(
            mavutil.mavlink,
            "MAV_FRAME_GLOBAL_RELATIVE_ALT_INT",
            6,
        )

        command = int(
            getattr(
                waypoint,
                "command",
                None,
            )
            or getattr(
                mavutil.mavlink,
                "MAV_CMD_NAV_WAYPOINT",
                16,
            )
        )

        mission_type = getattr(
            mavutil.mavlink,
            "MAV_MISSION_TYPE_MISSION",
            0,
        )

        # ====================================================
        # PARAMETERS
        # ====================================================

        hold_time = float(
            getattr(
                waypoint,
                "hold_time",
                0.0,
            )
        )

        acceptance_radius = float(
            getattr(
                waypoint,
                "acceptance_radius",
                0.0,
            )
        )

        yaw = float(
            getattr(
                waypoint,
                "yaw",
                0.0,
            )
        )

        current = 1 if sequence == 0 else 0

        autocontinue = 1

        latitude_int = int(
            round(
                waypoint.latitude
                * 10_000_000.0
            )
        )

        longitude_int = int(
            round(
                waypoint.longitude
                * 10_000_000.0
            )
        )

        altitude = float(
            waypoint.altitude
        )

        # ====================================================
        # ENCODE
        # ====================================================

        try:

            encoder = getattr(
                mav,
                "mission_item_int_encode",
                None,
            )

            if encoder is None:

                mav_log.error(TX, "mission_item_int_encode unavailable")

                return False

            try:

                message = encoder(
                    target_system,
                    target_component,
                    sequence,
                    frame,
                    command,
                    current,
                    autocontinue,
                    hold_time,
                    acceptance_radius,
                    0.0,
                    yaw,
                    latitude_int,
                    longitude_int,
                    altitude,
                    mission_type,
                )

            except TypeError:

                message = encoder(
                    target_system,
                    target_component,
                    sequence,
                    frame,
                    command,
                    current,
                    autocontinue,
                    hold_time,
                    acceptance_radius,
                    0.0,
                    yaw,
                    latitude_int,
                    longitude_int,
                    altitude,
                )

        except Exception as exc:

            mav_log.error(TX, f"MISSION_ITEM_INT encode: {type(exc).__name__}: {exc}")

            return False

        return self._send_message(
            message,
            f"MISSION_ITEM_INT seq={sequence}",
        )

    # ========================================================
    # SEND LEGACY MISSION ITEM
    # ========================================================

    def _send_mission_item(
        self,
        sequence: int,
    ) -> bool:

        mav = self._get_mavlink()

        if mav is None:

            return False

        sequence = int(
            sequence
        )

        waypoint = (
            self.mission.get_waypoint(
                sequence + 1
            )
        )

        if waypoint is None:

            return False

        target_system = (
            self._target_system()
        )

        target_component = (
            self._target_component()
        )

        frame = getattr(
            mavutil.mavlink,
            "MAV_FRAME_GLOBAL_RELATIVE_ALT",
            3,
        )

        command = int(
            getattr(
                waypoint,
                "command",
                None,
            )
            or getattr(
                mavutil.mavlink,
                "MAV_CMD_NAV_WAYPOINT",
                16,
            )
        )

        hold_time = float(
            getattr(
                waypoint,
                "hold_time",
                0.0,
            )
        )

        acceptance_radius = float(
            getattr(
                waypoint,
                "acceptance_radius",
                0.0,
            )
        )

        yaw = float(
            getattr(
                waypoint,
                "yaw",
                0.0,
            )
        )

        current = 1 if sequence == 0 else 0

        autocontinue = 1

        try:

            encoder = getattr(
                mav,
                "mission_item_encode",
                None,
            )

            if encoder is None:

                return False

            message = encoder(
                target_system,
                target_component,
                sequence,
                frame,
                command,
                current,
                autocontinue,
                hold_time,
                acceptance_radius,
                0.0,
                yaw,
                float(
                    waypoint.latitude
                ),
                float(
                    waypoint.longitude
                ),
                float(
                    waypoint.altitude
                ),
            )

        except Exception as exc:

            mav_log.error(TX, f"MISSION_ITEM encode: {type(exc).__name__}: {exc}")

            return False

        return self._send_message(
            message,
            f"MISSION_ITEM seq={sequence}",
        )

    # ========================================================
    # SET CURRENT
    # ========================================================

    def _handle_set_current(
        self,
        message,
    ):

        self._remember_sender(
            message
        )

        try:

            sequence = int(
                message.seq
            )

        except Exception:

            return

        waypoint = (
            self.mission.get_waypoint(
                sequence + 1
            )
        )

        if waypoint is None:

            mav_log.warn(MISSION, f"Invalid waypoint sequence={sequence}")

            return

        # ----------------------------------------------------
        # Zero-based internal index.
        # ----------------------------------------------------

        self.mission.current_index = (
            sequence
        )

        self.mission.started = True

        self.mission.finished = False

        mav_log.info(MISSION, f"Current waypoint -> WP{sequence + 1}")

    # ========================================================
    # ACK
    # ========================================================

    def _send_mission_ack(
        self,
        result,
    ) -> bool:

        mav = self._get_mavlink()

        if mav is None:

            return False

        target_system = (
            self._target_system()
        )

        target_component = (
            self._target_component()
        )

        mission_type = getattr(
            mavutil.mavlink,
            "MAV_MISSION_TYPE_MISSION",
            0,
        )

        try:

            encoder = getattr(
                mav,
                "mission_ack_encode",
                None,
            )

            if encoder is None:

                return False

            try:

                message = encoder(
                    target_system,
                    target_component,
                    int(result),
                    mission_type,
                )

            except TypeError:

                message = encoder(
                    target_system,
                    target_component,
                    int(result),
                )

        except Exception as exc:

            mav_log.error(MISSION, f"ACK encode: {type(exc).__name__}: {exc}")

            return False

        return self._send_message(
            message,
            f"MISSION_ACK={result}",
        )

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(
        self,
    ):

        return {

            "upload_active":
                self.upload_active,

            "expected_count":
                self.expected_count,

            "received_count":
                self.received_count,

            "current_sequence":
                self.expected_seq,

            "mission_count":
                self.mission.count(),

            "download_active":
                self.download_active,

            "download_index":
                self.download_index,

            "sender_system":
                self.sender_system,

            "sender_component":
                self.sender_component,
        }