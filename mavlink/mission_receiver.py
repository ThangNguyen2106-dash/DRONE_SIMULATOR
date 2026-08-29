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
from simulator.mission_tasks import MissionTask


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
    ):

        self.connection = connection

        self.mission = mission

        self.system_id = int(
            system_id
        )

        self.component_id = int(
            component_id
        )

        # ====================================================
        # UPLOAD STATE
        # ====================================================

        self.upload_active = False

        self.expected_count = 0

        self.expected_seq = 0

        self.received_count = 0

        # Mission-level speed command (MAV_CMD_DO_CHANGE_SPEED).
        self.pending_speed = 5.0
        self.pending_tasks = []

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

            print(
                "[MISSION TX ERROR] "
                f"{description}: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return False

        if not result:

            print(
                "[MISSION TX FAILED] "
                f"{description}"
            )

            return False

        print(
            "[MISSION TX] "
            f"{description}"
        )

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

        print(
            "[MISSION RX] "
            f"MISSION_COUNT={count}"
        )

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

            print(
                "[MISSION] Empty mission accepted"
            )

            return

        # ====================================================
        # SAFETY LIMIT
        # ====================================================

        if count > 1000:

            self._send_mission_ack(
                mavutil.mavlink.MAV_MISSION_ERROR
            )

            print(
                "[MISSION] Mission rejected: "
                f"too many items ({count})"
            )

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
        self.pending_tasks = []

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

            print(
                "[MISSION RX] "
                "Unexpected MISSION_ITEM_INT"
            )

            return

        self._remember_sender(
            message
        )

        try:

            seq = int(
                message.seq
            )

        except Exception:

            print(
                "[MISSION RX] "
                "Invalid MISSION_ITEM_INT seq"
            )

            return

        # ====================================================
        # SEQUENCE
        # ====================================================

        if seq != self.expected_seq:

            print(
                "[MISSION RX] "
                f"Unexpected seq={seq}, "
                f"expected={self.expected_seq}"
            )

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

            print(
                "[MISSION RX] "
                "Unexpected MISSION_ITEM"
            )

            return

        self._remember_sender(
            message
        )

        try:

            seq = int(
                message.seq
            )

        except Exception:

            print(
                "[MISSION RX] "
                "Invalid MISSION_ITEM seq"
            )

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
    # STORE INT ITEM
    # ========================================================

    def _store_task_command(self, command: int, message) -> bool:
        """Convert MAVLink action commands into tasks for the NAV item they follow.

        In a MAVLink mission, DO commands are normally placed immediately after
        the NAV item they belong to. During upload the previous NAV item is
        therefore the correct place to attach the action.
        """
        image_start = getattr(mavutil.mavlink, "MAV_CMD_IMAGE_START_CAPTURE", 2000)
        image_stop = getattr(mavutil.mavlink, "MAV_CMD_IMAGE_STOP_CAPTURE", 2001)
        cam_trigger = getattr(mavutil.mavlink, "MAV_CMD_DO_SET_CAM_TRIGG_DIST", 206)
        servo = getattr(mavutil.mavlink, "MAV_CMD_DO_SET_SERVO", 183)
        gimbal = getattr(mavutil.mavlink, "MAV_CMD_DO_GIMBAL_MANAGER_PITCHYAW", 1000)
        rtl = getattr(mavutil.mavlink, "MAV_CMD_NAV_RETURN_TO_LAUNCH", 20)
        relay = getattr(mavutil.mavlink, "MAV_CMD_DO_SET_RELAY", 181)
        roi = getattr(mavutil.mavlink, "MAV_CMD_DO_SET_ROI", 201)
        nav_delay = getattr(mavutil.mavlink, "MAV_CMD_NAV_DELAY", 93)

        task = None
        if command == image_start:
            task = MissionTask("PHOTO", {
                "interval": float(getattr(message, "param2", 0.0)),
                "count": int(max(1, getattr(message, "param3", 1))),
            })
        elif command == image_stop:
            task = MissionTask("PHOTO_STOP")
        elif command == cam_trigger:
            task = MissionTask("CAMERA_TRIGGER_DISTANCE", {
                "trigger_distance_m": float(getattr(message, "param1", 0.0)),
            })
        elif command == servo:
            task = MissionTask("PAYLOAD_RELEASE", {
                "servo": int(getattr(message, "param1", 0)),
                "pwm": float(getattr(message, "param2", 0.0)),
            })
        elif command == gimbal:
            task = MissionTask("GIMBAL", {
                "pitch": float(getattr(message, "param1", 0.0)),
                "yaw": float(getattr(message, "param2", 0.0)),
            })
        elif command == rtl:
            task = MissionTask("RTL", {})
        elif command == relay:
            task = MissionTask("RELAY", {
                "relay": int(getattr(message, "param1", 0)),
                "state": int(getattr(message, "param2", 0)),
            })
        elif command == roi:
            task = MissionTask("ROI", {
                "roi_mode": int(getattr(message, "param1", 0)),
                "latitude": float(getattr(message, "x", 0.0)) / 1e7,
                "longitude": float(getattr(message, "y", 0.0)) / 1e7,
                "altitude": float(getattr(message, "z", 0.0)),
            })
        elif command == nav_delay:
            task = MissionTask("HOLD", {
                "duration": max(0.0, float(getattr(message, "param1", 0.0)))
            })
        else:
            return False

        # Attach to the most recently received NAV item. If none exists yet,
        # retain the old pending behavior so uploads remain tolerant.
        if self.staging_mission.count() > 0:
            wp = self.staging_mission.get_waypoint(self.staging_mission.count())
            wp.tasks.append(task)
            print(f"[MISSION RX] {task.task_type} attached to WP{wp.index}")
        else:
            self.pending_tasks.append(task)
            print(f"[MISSION RX] {task.task_type} queued for next waypoint")
        return True

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
            print(f"[MISSION RX] DO_CHANGE_SPEED -> {self.pending_speed:.2f} m/s")
            return True

        if self._store_task_command(command, message):
            return True

        supported_commands = {
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            getattr(mavutil.mavlink, "MAV_CMD_NAV_LOITER_TIME", 19),
        }

        if command not in supported_commands:

            print(
                "[MISSION RX] "
                f"Unsupported command={command}"
            )

            return False

        # ====================================================
        # GPS
        # ====================================================

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

        # ====================================================
        # COORDINATE VALIDATION
        # ====================================================

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
                name=f"WP{sequence + 1}",
                command=command,
                acceptance_radius=acceptance_radius or 0.0,
                yaw=yaw or 0.0,
                tasks=list(self.pending_tasks),
            )
        )

        # Preserve the original MAVLink sequence.
        waypoint.source_seq = sequence
        self.pending_tasks.clear()

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

        print(
            "[MISSION RX] "
            f"WP{waypoint.index}: "
            f"LAT={latitude:.7f} "
            f"LON={longitude:.7f} "
            f"ALT={altitude:.2f} "
            f"HOLD={hold_time:.1f}s"
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
            print(f"[MISSION RX] DO_CHANGE_SPEED -> {self.pending_speed:.2f} m/s")
            return True

        if self._store_task_command(command, message):
            return True

        supported_commands = {
            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            getattr(mavutil.mavlink, "MAV_CMD_NAV_LOITER_TIME", 19),
        }

        if command not in supported_commands:

            print(
                "[MISSION RX] "
                f"Unsupported command={command}"
            )

            return False

        # ====================================================
        # VALIDATION
        # ====================================================

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
                name=f"WP{sequence + 1}",
                command=command,
                acceptance_radius=max(0.0, float(getattr(message, "param2", 0.0))),
                yaw=float(getattr(message, "param4", 0.0)),
                tasks=list(self.pending_tasks),
            )
        )

        waypoint.source_seq = sequence
        self.pending_tasks.clear()

        print(
            "[MISSION RX] "
            f"WP{waypoint.index}: "
            f"LAT={latitude:.7f} "
            f"LON={longitude:.7f} "
            f"ALT={altitude:.2f} "
            f"HOLD={hold_time:.1f}s"
        )

        return True

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

        print(
            "[MISSION RX] "
            f"Unknown frame={frame}; "
            f"using z={altitude}"
        )

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

            print(
                "[MISSION TX ERROR] "
                "MAVLink encoder unavailable"
            )

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

                print(
                    "[MISSION TX ERROR] "
                    "mission_request_int_encode "
                    "unavailable"
                )

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

            print(
                "[MISSION TX ERROR] "
                "MISSION_REQUEST_INT encode: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

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
                    tasks=list(getattr(waypoint, "tasks", []) or []),
                )
            )

            # Preserve optional attributes.

            for attribute in (
                "acceptance_radius",
                "yaw",
                "command",
                "source_seq",
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

        print(
            "[MISSION] Upload complete"
        )

        print(
            "[MISSION] "
            f"{self.mission.count()} "
            "waypoints accepted"
        )

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
        self.pending_tasks = []

        self.mission.clear()

        print(
            "[MISSION] Mission cleared by GCS"
        )

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

        print(
            "[MISSION RX] "
            "MISSION_REQUEST_LIST "
            f"count={count}"
        )

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

            print(
                "[MISSION TX ERROR] "
                "MISSION_COUNT encode: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

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

            print(
                "[MISSION TX] "
                f"Waypoint seq={sequence} "
                "does not exist"
            )

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

        command = getattr(
            mavutil.mavlink,
            "MAV_CMD_NAV_WAYPOINT",
            16,
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

                print(
                    "[MISSION TX ERROR] "
                    "mission_item_int_encode "
                    "unavailable"
                )

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

            print(
                "[MISSION TX ERROR] "
                "MISSION_ITEM_INT encode: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

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

        command = getattr(
            mavutil.mavlink,
            "MAV_CMD_NAV_WAYPOINT",
            16,
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

            print(
                "[MISSION TX ERROR] "
                "MISSION_ITEM encode: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

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

            print(
                "[MISSION] "
                f"Invalid waypoint sequence={sequence}"
            )

            return

        # ----------------------------------------------------
        # Zero-based internal index.
        # ----------------------------------------------------

        self.mission.current_index = (
            sequence
        )

        self.mission.started = True

        self.mission.finished = False

        print(
            "[MISSION] "
            f"Current waypoint -> "
            f"WP{sequence + 1}"
        )

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

            print(
                "[MISSION ACK ERROR] "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

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