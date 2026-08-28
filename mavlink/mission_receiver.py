from typing import Optional

from pymavlink import mavutil

from simulator.mission import Mission


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

        self.system_id = system_id

        self.component_id = component_id

        # ====================================================
        # UPLOAD STATE
        # ====================================================

        self.upload_active = False

        self.expected_count = 0

        self.expected_seq = 0

        self.received_count = 0

        # ====================================================
        # STAGING MISSION
        #
        # The current mission is not replaced until the
        # complete upload has been received.
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
        # DOWNLOAD REQUEST
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
            f"[MISSION RX] "
            f"MISSION_COUNT={count}"
        )

        # ----------------------------------------------------
        # Empty mission
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Protect against unreasonable mission sizes.
        # ----------------------------------------------------

        if count > 1000:

            self._send_mission_ack(
                mavutil.mavlink.MAV_MISSION_ERROR
            )

            print(
                "[MISSION] Mission rejected: "
                f"too many items ({count})"
            )

            return

        # ----------------------------------------------------
        # Start staging upload.
        # ----------------------------------------------------

        self.staging_mission.clear()

        self.upload_active = True

        self.expected_count = count

        self.expected_seq = 0

        self.received_count = 0

        # ----------------------------------------------------
        # New upload supersedes download.
        # ----------------------------------------------------

        self.download_active = False

        self.download_index = 0

        # ----------------------------------------------------
        # Request first item.
        # ----------------------------------------------------

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

            return

        # ----------------------------------------------------
        # Sequence validation.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Store mission item.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Upload finished.
        # ----------------------------------------------------

        if (
            self.received_count
            >= self.expected_count
        ):

            self._finish_upload()

            return

        # ----------------------------------------------------
        # Request next item.
        # ----------------------------------------------------

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

            return

        self._remember_sender(
            message
        )

        try:

            seq = int(
                message.seq
            )

        except Exception:

            return

        if seq != self.expected_seq:

            self._request_item(
                self.expected_seq
            )

            return

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

        if (
            self.received_count
            >= self.expected_count
        ):

            self._finish_upload()

            return

        self._request_item(
            self.expected_seq
        )

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

        # ----------------------------------------------------
        # Supported navigation commands.
        # ----------------------------------------------------

        supported_commands = {

            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,

            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,

            mavutil.mavlink.MAV_CMD_NAV_LAND,
        }

        if command not in supported_commands:

            print(
                "[MISSION RX] "
                f"Unsupported command={command}"
            )

            return False

        # ----------------------------------------------------
        # GPS coordinates.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Coordinate validation.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # MAV_CMD_NAV_WAYPOINT:
        #
        # param2 = acceptance radius
        # param3 = pass through
        # param4 = yaw
        #
        # param1 is hold time.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Default simulator speed.
        # ----------------------------------------------------

        speed = 5.0

        waypoint = (
            self.staging_mission
            .add_waypoint(
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                speed=speed,
                hold_time=hold_time,
                name=f"WP{sequence + 1}",
            )
        )

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

        supported_commands = {

            mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,

            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,

            mavutil.mavlink.MAV_CMD_NAV_LAND,
        }

        if command not in supported_commands:

            print(
                "[MISSION RX] "
                f"Unsupported command={command}"
            )

            return False

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

        waypoint = (
            self.staging_mission
            .add_waypoint(
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                speed=5.0,
                hold_time=hold_time,
                name=f"WP{sequence + 1}",
            )
        )

        print(
            "[MISSION RX] "
            f"WP{waypoint.index}: "
            f"LAT={latitude:.7f} "
            f"LON={longitude:.7f} "
            f"ALT={altitude:.2f}"
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

        altitude = float(
            message.z
        )

        # ----------------------------------------------------
        # Relative altitude.
        #
        # Simulator Home altitude is normally 0m.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Absolute altitude.
        # ----------------------------------------------------

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

            # Home altitude in this simulator is represented
            # by the local altitude reference.
            #
            # Therefore a relative altitude of 50m becomes
            # 50m in simulator coordinates.
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
    ):

        mav = self._get_mav()

        if mav is None:

            return

        target_system = (
            self.sender_system
            if self.sender_system is not None
            else 0
        )

        target_component = (
            self.sender_component
            if self.sender_component is not None
            else 0
        )

        try:

            mav.mission_request_int_send(
                target_system,
                target_component,
                int(sequence),
            )

        except TypeError:

            try:

                mav.mission_request_int_send(
                    target_system,
                    target_component,
                    int(sequence),
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
                )

            except Exception as exc:

                print(
                    "[MISSION TX ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

                return

        except Exception as exc:

            print(
                "[MISSION TX ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            return

        print(
            "[MISSION TX] "
            f"MISSION_REQUEST_INT seq={sequence}"
        )

    # ========================================================
    # FINISH UPLOAD
    # ========================================================

    def _finish_upload(self):

        # ----------------------------------------------------
        # Replace active mission only after all items
        # have been successfully received.
        # ----------------------------------------------------

        self.mission.clear()

        for waypoint in (
            self.staging_mission.get_all()
        ):

            self.mission.add_waypoint(
                latitude=waypoint.latitude,
                longitude=waypoint.longitude,
                altitude=waypoint.altitude,
                speed=waypoint.speed,
                hold_time=waypoint.hold_time,
                name=waypoint.name,
            )

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

        print(
            "[MISSION] Upload complete"
        )

        print(
            "[MISSION] "
            f"{self.mission.count()} "
            "waypoints accepted"
        )

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

        print(
            "[MISSION] "
            "Mission cleared by GCS"
        )

        self._send_mission_ack(
            mavutil.mavlink.MAV_MISSION_ACCEPTED
        )

    # ========================================================
    # MISSION REQUEST LIST
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
            f"MISSION_REQUEST_LIST "
            f"count={count}"
        )

        self.download_active = True

        self.download_index = 0

        self._send_mission_count(
            count
        )

    # ========================================================
    # MISSION REQUEST INT
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
    # LEGACY MISSION REQUEST
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
    ):

        mav = self._get_mav()

        if mav is None:

            return

        target_system = (
            self.sender_system
            if self.sender_system is not None
            else 0
        )

        target_component = (
            self.sender_component
            if self.sender_component is not None
            else 0
        )

        try:

            mav.mission_count_send(
                target_system,
                target_component,
                int(count),
            )

        except TypeError:

            try:

                mav.mission_count_send(
                    target_system,
                    target_component,
                    int(count),
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
                )

            except Exception as exc:

                print(
                    "[MISSION TX ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

                return

        except Exception as exc:

            print(
                "[MISSION TX ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            return

        print(
            "[MISSION TX] "
            f"MISSION_COUNT={count}"
        )

    # ========================================================
    # SEND MISSION ITEM INT
    # ========================================================

    def _send_mission_item_int(
        self,
        sequence: int,
    ):

        mav = self._get_mav()

        if mav is None:

            return

        waypoint = (
            self.mission.get_waypoint(
                sequence + 1
            )
        )

        if waypoint is None:

            return

        target_system = (
            self.sender_system
            if self.sender_system is not None
            else 0
        )

        target_component = (
            self.sender_component
            if self.sender_component is not None
            else 0
        )

        try:

            mav.mission_item_int_send(
                target_system,
                target_component,
                int(sequence),
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,
                1,
                float(waypoint.hold_time),
                0.0,
                0.0,
                0.0,
                int(
                    round(
                        waypoint.latitude
                        * 10_000_000.0
                    )
                ),
                int(
                    round(
                        waypoint.longitude
                        * 10_000_000.0
                    )
                ),
                float(waypoint.altitude),
            )

        except TypeError:

            try:

                mav.mission_item_int_send(
                    target_system,
                    target_component,
                    int(sequence),
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    0,
                    1,
                    float(waypoint.hold_time),
                    0.0,
                    0.0,
                    0.0,
                    int(
                        round(
                            waypoint.latitude
                            * 10_000_000.0
                        )
                    ),
                    int(
                        round(
                            waypoint.longitude
                            * 10_000_000.0
                        )
                    ),
                    float(waypoint.altitude),
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
                )

            except Exception as exc:

                print(
                    "[MISSION TX ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

                return

        except Exception as exc:

            print(
                "[MISSION TX ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            return

        print(
            "[MISSION TX] "
            f"MISSION_ITEM_INT seq={sequence}"
        )

    # ========================================================
    # SEND LEGACY ITEM
    # ========================================================

    def _send_mission_item(
        self,
        sequence: int,
    ):

        mav = self._get_mav()

        if mav is None:

            return

        waypoint = (
            self.mission.get_waypoint(
                sequence + 1
            )
        )

        if waypoint is None:

            return

        target_system = (
            self.sender_system
            if self.sender_system is not None
            else 0
        )

        target_component = (
            self.sender_component
            if self.sender_component is not None
            else 0
        )

        try:

            mav.mission_item_send(
                target_system,
                target_component,
                int(sequence),
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,
                1,
                float(waypoint.hold_time),
                0.0,
                0.0,
                0.0,
                float(waypoint.latitude),
                float(waypoint.longitude),
                float(waypoint.altitude),
            )

        except Exception as exc:

            print(
                "[MISSION TX ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            return

        print(
            "[MISSION TX] "
            f"MISSION_ITEM seq={sequence}"
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
        # Mission internal index is zero-based.
        # MAVLink sequence is also zero-based.
        # ----------------------------------------------------

        self.mission.current_index = (
            sequence
        )

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
    ):

        mav = self._get_mav()

        if mav is None:

            return

        target_system = (
            self.sender_system
            if self.sender_system is not None
            else 0
        )

        target_component = (
            self.sender_component
            if self.sender_component is not None
            else 0
        )

        try:

            mav.mission_ack_send(
                target_system,
                target_component,
                result,
            )

        except TypeError:

            try:

                mav.mission_ack_send(
                    target_system,
                    target_component,
                    result,
                    mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
                )

            except Exception as exc:

                print(
                    "[MISSION ACK ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

                return

        except Exception as exc:

            print(
                "[MISSION ACK ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            return

        print(
            "[MISSION TX] "
            f"MISSION_ACK={result}"
        )

    # ========================================================
    # MAV OBJECT
    # ========================================================

    def _get_mav(self):

        if self.connection is None:

            return None

        mav_connection = getattr(
            self.connection,
            "connection",
            None,
        )

        if mav_connection is None:

            return None

        return getattr(
            mav_connection,
            "mav",
            None,
        )

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self):

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
        }