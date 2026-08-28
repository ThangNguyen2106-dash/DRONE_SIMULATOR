from typing import Optional

from pymavlink import mavutil

from .mav_logger import mav_log, COMMAND


class CommandReceiver:

    # ============================================================
    # MINIMAL PARAMETER SET
    #
    # This simulator has no real parameter storage. Ground
    # stations (Mission Planner / QGroundControl) hang on
    # "Getting params..." forever if PARAM_REQUEST_LIST is
    # never answered, so we advertise a small fixed set just
    # to let the parameter download complete.
    # ============================================================

    DEFAULT_PARAMS = {
        "SYSID_THISMAV": 1.0,
        "ARMING_CHECK": 1.0,
        "FRAME_CLASS": 1.0,
        "FRAME_TYPE": 1.0,
        "FS_THR_ENABLE": 0.0,
    }

    def __init__(
        self,
        connection,
        controller=None,
        drone=None,
    ):

        self.connection = connection

        self.controller = controller

        self.params = dict(
            self.DEFAULT_PARAMS
        )

        # ----------------------------------------------------
        # Prefer explicit drone.
        # Otherwise try to get it from controller.
        # ----------------------------------------------------

        if drone is not None:

            self.drone = drone

        elif controller is not None:

            self.drone = getattr(
                controller,
                "drone",
                None,
            )

        else:

            self.drone = None

    # ========================================================
    # PROCESS MESSAGE
    # ========================================================

    def process(
        self,
        message,
    ):

        if message is None:

            return False

        try:

            message_type = (
                message.get_type()
            )

        except Exception:

            return False

        # ----------------------------------------------------
        # Ignore MAVLink protocol markers.
        # ----------------------------------------------------

        if message_type in (
            "BAD_DATA",
            "UNKNOWN",
        ):

            return False

        # ====================================================
        # COMMAND_LONG
        # ====================================================

        if message_type == "COMMAND_LONG":

            return self._handle_command_long(
                message
            )

        # ====================================================
        # COMMAND_INT
        # ====================================================

        if message_type == "COMMAND_INT":

            return self._handle_command_int(
                message
            )

        # ====================================================
        # SET_MODE
        # ====================================================

        if message_type == "SET_MODE":

            return self._handle_set_mode(
                message
            )

        # ====================================================
        # SET_POSITION_TARGET_GLOBAL_INT
        # ====================================================

        if (
            message_type
            == "SET_POSITION_TARGET_GLOBAL_INT"
        ):

            return self._handle_position_target(
                message
            )

        # ====================================================
        # PARAM_REQUEST_LIST
        # ====================================================

        if message_type == "PARAM_REQUEST_LIST":

            return self._handle_param_request_list()

        # ====================================================
        # PARAM_REQUEST_READ
        # ====================================================

        if message_type == "PARAM_REQUEST_READ":

            return self._handle_param_request_read(
                message
            )

        # ====================================================
        # PARAM_SET
        # ====================================================

        if message_type == "PARAM_SET":

            return self._handle_param_set(
                message
            )

        return False

    # ========================================================
    # PARAM HELPERS
    # ========================================================

    @staticmethod
    def _param_id_of(message) -> str:

        param_id = getattr(
            message,
            "param_id",
            "",
        )

        if isinstance(param_id, bytes):

            param_id = param_id.decode(
                "ascii",
                errors="ignore",
            )

        return str(param_id).rstrip("\x00")

    # --------------------------------------------------------

    def _send_param_value(
        self,
        name: str,
        value: float,
        index: int,
    ) -> bool:

        if self.connection is None:
            return False

        try:

            message = (
                self.connection.mavlink
                .param_value_encode(
                    name.encode("ascii"),
                    float(value),
                    mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
                    len(self.params),
                    index,
                )
            )

            return bool(
                self.connection.send(message)
            )

        except Exception as exc:

            mav_log.error(COMMAND, f"PARAM TX {name}: {exc}")

            return False

    # ========================================================
    # PARAM_REQUEST_LIST
    # ========================================================

    def _handle_param_request_list(self) -> bool:

        mav_log.info(COMMAND, f"PARAM_REQUEST_LIST -> sending {len(self.params)} params")

        ok = True

        for index, (name, value) in enumerate(
            self.params.items()
        ):

            if not self._send_param_value(
                name,
                value,
                index,
            ):

                ok = False

        return ok

    # ========================================================
    # PARAM_REQUEST_READ
    # ========================================================

    def _handle_param_request_read(
        self,
        message,
    ) -> bool:

        param_index = int(
            getattr(
                message,
                "param_index",
                -1,
            )
        )

        names = list(self.params.keys())

        if 0 <= param_index < len(names):

            name = names[param_index]

        else:

            name = self._param_id_of(message)

        if name not in self.params:

            mav_log.warn(COMMAND, f"PARAM_REQUEST_READ -> unknown param {name!r}")

            return False

        index = names.index(name) if name in names else 0

        return self._send_param_value(
            name,
            self.params[name],
            index,
        )

    # ========================================================
    # PARAM_SET
    # ========================================================

    def _handle_param_set(
        self,
        message,
    ) -> bool:

        name = self._param_id_of(message)

        value = float(
            getattr(
                message,
                "param_value",
                0.0,
            )
        )

        self.params[name] = value

        mav_log.info(COMMAND, f"PARAM_SET -> {name} = {value}")

        names = list(self.params.keys())

        return self._send_param_value(
            name,
            value,
            names.index(name),
        )

    # ========================================================
    # COMMAND_LONG
    # ========================================================

    def _handle_command_long(
        self,
        message,
    ):

        command = int(
            getattr(
                message,
                "command",
                -1,
            )
        )

        # ----------------------------------------------------
        # MAV_CMD_COMPONENT_ARM_DISARM = 400
        # ----------------------------------------------------

        if command == 400:

            return self._handle_arm_disarm(
                message
            )

        # ----------------------------------------------------
        # MAV_CMD_NAV_TAKEOFF = 22
        # ----------------------------------------------------

        if command == 22:

            return self._handle_takeoff(
                message
            )

        # ----------------------------------------------------
        # MAV_CMD_NAV_LAND = 21
        # ----------------------------------------------------

        if command == 21:

            return self._handle_land()

        # ----------------------------------------------------
        # MAV_CMD_NAV_RETURN_TO_LAUNCH = 20
        # ----------------------------------------------------

        if command == 20:

            return self._handle_rtl()

        # ----------------------------------------------------
        # MAV_CMD_MISSION_START = 300
        # ----------------------------------------------------

        if command == 300:

            return self._handle_mission_start()

        # ----------------------------------------------------
        # MAV_CMD_DO_SET_MODE = 176
        # ----------------------------------------------------

        if command == 176:

            return self._handle_do_set_mode(
                message
            )

        return False

    # ========================================================
    # COMMAND_INT
    # ========================================================

    def _handle_command_int(
        self,
        message,
    ):

        command = int(
            getattr(
                message,
                "command",
                -1,
            )
        )

        # ----------------------------------------------------
        # ARM / DISARM
        # ----------------------------------------------------

        if command == 400:

            return self._handle_arm_disarm(
                message
            )

        # ----------------------------------------------------
        # TAKEOFF
        # ----------------------------------------------------

        if command == 22:

            return self._handle_takeoff(
                message
            )

        # ----------------------------------------------------
        # LAND
        # ----------------------------------------------------

        if command == 21:

            return self._handle_land()

        # ----------------------------------------------------
        # RTL
        # ----------------------------------------------------

        if command == 20:

            return self._handle_rtl()

        # ----------------------------------------------------
        # MISSION START
        # ----------------------------------------------------

        if command == 300:

            return self._handle_mission_start()

        return False

    # ========================================================
    # ARM / DISARM
    # ========================================================

    def _handle_arm_disarm(
        self,
        message,
    ):

        if self.drone is None:

            return False

        param1 = float(
            getattr(
                message,
                "param1",
                0.0,
            )
        )

        # ----------------------------------------------------
        # param1:
        #
        # 1 = ARM
        # 0 = DISARM
        # ----------------------------------------------------

        if param1 >= 0.5:

            result = self.drone.arm()

            mav_log.info(COMMAND, f"ARM -> {result}")

            return bool(result)

        result = self.drone.disarm()

        mav_log.info(COMMAND, f"DISARM -> {result}")

        return bool(result)

    # ========================================================
    # TAKEOFF
    # ========================================================

    def _handle_takeoff(
        self,
        message,
    ):

        if self.drone is None:

            return False

        # ----------------------------------------------------
        # COMMAND_LONG TAKEOFF:
        #
        # param7 = altitude
        #
        # COMMAND_INT TAKEOFF:
        #
        # z = altitude
        # ----------------------------------------------------

        altitude = getattr(
            message,
            "param7",
            None,
        )

        if altitude is None:

            altitude = getattr(
                message,
                "z",
                0.0,
            )

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

            # Some GCS messages may leave
            # the altitude empty.
            #
            # Use a safe simulator default.
            altitude = 10.0

        result = (
            self.drone.takeoff(
                altitude
            )
        )

        mav_log.info(COMMAND, f"TAKEOFF {altitude:.1f}m -> {result}")

        return bool(result)

    # ========================================================
    # LAND
    # ========================================================

    def _handle_land(self):

        if self.drone is None:

            return False

        result = (
            self.drone.land()
        )

        mav_log.info(COMMAND, f"LAND -> {result}")

        return bool(result)

    # ========================================================
    # RTL
    # ========================================================

    def _handle_rtl(self):

        if self.drone is None:

            return False

        result = (
            self.drone.rtl()
        )

        mav_log.info(COMMAND, f"RTL -> {result}")

        return bool(result)

    # ========================================================
    # MISSION START
    # ========================================================

    def _handle_mission_start(self):

        if self.drone is None:

            return False

        result = (
            self.drone.start_mission()
        )

        mav_log.info(COMMAND, f"MISSION START -> {result}")

        return bool(result)

    # ========================================================
    # SET MODE
    # ========================================================

    def _handle_set_mode(
        self,
        message,
    ):

        custom_mode = int(
            getattr(
                message,
                "custom_mode",
                0,
            )
        )

        return self._set_mode_from_value(
            custom_mode
        )

    # ========================================================
    # DO SET MODE
    # ========================================================

    def _handle_do_set_mode(
        self,
        message,
    ):

        # COMMAND_LONG 176:
        #
        # param1 = base mode
        # param2 = custom mode

        custom_mode = int(
            getattr(
                message,
                "param2",
                0,
            )
        )

        return self._set_mode_from_value(
            custom_mode
        )

    # ========================================================
    # MODE VALUE
    # ========================================================

    def _set_mode_from_value(
        self,
        custom_mode: int,
    ):

        if self.drone is None:

            return False

        # ----------------------------------------------------
        # ArduPilot Copter custom modes:
        #
        # 0  STABILIZE
        # 1  ACRO
        # 2  ALT_HOLD
        # 3  AUTO
        # 4  GUIDED
        # 5  LOITER
        # 6  RTL
        # 9  LAND
        # 16 POSHOLD
        #
        # The simulator only implements the modes
        # that have actual simulation behaviour.
        # ----------------------------------------------------

        if custom_mode == 6:

            return self._handle_rtl()

        if custom_mode == 9:

            return self._handle_land()

        if custom_mode == 3:

            return self._handle_mission_start()

        if custom_mode == 4:

            self.drone.state.mode = "GUIDED"

            mav_log.info(COMMAND, "MODE -> GUIDED")

            return True

        if custom_mode == 5:

            self.drone.state.mode = "HOLD"

            self.drone.set_speed(
                0.0
            )

            mav_log.info(COMMAND, "MODE -> HOLD")

            return True

        return False

    # ========================================================
    # POSITION TARGET
    # ========================================================

    def _handle_position_target(
        self,
        message,
    ):

        if self.drone is None:

            return False

        # ----------------------------------------------------
        # Global position target:
        #
        # lat/lon are int32 degrees * 1e7
        # z is altitude
        # ----------------------------------------------------

        lat_raw = getattr(
            message,
            "lat_int",
            None,
        )

        lon_raw = getattr(
            message,
            "lon_int",
            None,
        )

        altitude = getattr(
            message,
            "alt",
            None,
        )

        if (
            lat_raw is None
            or
            lon_raw is None
            or
            altitude is None
        ):

            return False

        try:

            lat = (
                float(lat_raw)
                / 10_000_000.0
            )

            lon = (
                float(lon_raw)
                / 10_000_000.0
            )

            altitude = float(
                altitude
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        # ----------------------------------------------------
        # Validate coordinates.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Use the normal navigation system.
        # ----------------------------------------------------

        self.drone.navigation.set_target(
            lat=lat,
            lon=lon,
            alt=altitude,
        )

        self.drone.rtl_active = False

        self.drone.mission_navigator.stop()

        self.drone.state.mode = "GUIDED"

        mav_log.info(COMMAND, f"POSITION TARGET {lat:.7f}, {lon:.7f}, {altitude:.1f}m")

        return True