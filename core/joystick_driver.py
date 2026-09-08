"""
Hardware Joystick Driver for Drone Simulator.

Supports RadioMaster TX16S, OpenTX/EdgeTX RC Transmitters, Xbox/PS Gamepads,
and any standard USB HID Joystick on Windows via native winmm.dll (zero external dependencies).
"""

import sys
import time
import ctypes
from ctypes import wintypes
from typing import Dict, List, Optional, Set, Tuple


class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("dwXpos", wintypes.DWORD),
        ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD),
        ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD),
        ("dwVpos", wintypes.DWORD),
        ("dwButtons", wintypes.DWORD),
        ("dwButtonNumber", wintypes.DWORD),
        ("dwPOV", wintypes.DWORD),
        ("dwReserved1", wintypes.DWORD),
        ("dwReserved2", wintypes.DWORD),
    ]


class JOYCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("szPname", wintypes.WCHAR * 32),
        ("wXmin", wintypes.UINT),
        ("wXmax", wintypes.UINT),
        ("wYmin", wintypes.UINT),
        ("wYmax", wintypes.UINT),
        ("wZmin", wintypes.UINT),
        ("wZmax", wintypes.UINT),
        ("wNumButtons", wintypes.UINT),
        ("wPeriodMin", wintypes.UINT),
        ("wPeriodMax", wintypes.UINT),
        ("wRmin", wintypes.UINT),
        ("wRmax", wintypes.UINT),
        ("wUmin", wintypes.UINT),
        ("wUmax", wintypes.UINT),
        ("wVmin", wintypes.UINT),
        ("wVmax", wintypes.UINT),
        ("wCaps", wintypes.UINT),
        ("wMaxAxes", wintypes.UINT),
        ("wNumAxes", wintypes.UINT),
        ("wMaxButtons", wintypes.UINT),
        ("szRegKey", wintypes.WCHAR * 32),
        ("szOEMVxD", wintypes.WCHAR * 260),
    ]


JOY_RETURNALL = 0xFF
JOYERR_NOERROR = 0


class JoystickDriver:
    """
    Direct low-latency hardware joystick reader for Windows.
    """

    AXIS_NAMES = ["X", "Y", "Z", "R", "U", "V"]

    def __init__(
        self,
        device_id: int = 0,
        deadzone: float = 0.03,
        axis_pitch: str = "X",      # CH1
        axis_roll: str = "Y",       # CH2
        axis_throttle: str = "Z",   # CH3
        axis_yaw: str = "R",        # CH4 (or U / V)
        invert_pitch: bool = False, # Invert false by default
        invert_roll: bool = False,
        invert_throttle: bool = True,
        invert_yaw: bool = False,
    ):
        self.device_id = int(device_id)
        self.deadzone = float(deadzone)

        # Configurable Axis Mapping
        self.axis_pitch = axis_pitch
        self.axis_roll = axis_roll
        self.axis_throttle = axis_throttle
        self.axis_yaw = axis_yaw

        # Configurable Inversions
        self.invert_pitch = invert_pitch
        self.invert_roll = invert_roll
        self.invert_throttle = invert_throttle
        self.invert_yaw = invert_yaw

        self.connected = False
        self.device_name = "None"
        self.num_axes = 0
        self.num_buttons = 0

        self._winmm = None
        if sys.platform == "win32":
            try:
                self._winmm = ctypes.WinDLL("winmm")
            except Exception as exc:
                print(f"[JOYSTICK] winmm.dll load error: {exc}")

        self._last_buttons_mask = 0
        self._last_scan_time = 0.0
        self._scan_interval = 1.0  # scan for devices every 1s if disconnected

        self.scan_and_connect()

    def set_axis_mapping(self, pitch: str = None, roll: str = None, throttle: str = None, yaw: str = None):
        if pitch is not None: self.axis_pitch = str(pitch).upper()
        if roll is not None: self.axis_roll = str(roll).upper()
        if throttle is not None: self.axis_throttle = str(throttle).upper()
        if yaw is not None: self.axis_yaw = str(yaw).upper()

    def set_inverts(self, pitch: bool = None, roll: bool = None, throttle: bool = None, yaw: bool = None):
        if pitch is not None: self.invert_pitch = bool(pitch)
        if roll is not None: self.invert_roll = bool(roll)
        if throttle is not None: self.invert_throttle = bool(throttle)
        if yaw is not None: self.invert_yaw = bool(yaw)

    def scan_and_connect(self) -> bool:
        """Scan for available joysticks and connect to the first available or specified device."""
        if self._winmm is None:
            self.connected = False
            return False

        now = time.monotonic()
        self._last_scan_time = now

        num_devs = self._winmm.joyGetNumDevs()
        if num_devs <= 0:
            self.connected = False
            return False

        check_ids = [self.device_id] + [i for i in range(num_devs) if i != self.device_id]

        for dev_id in check_ids:
            ji = JOYINFOEX()
            ji.dwSize = ctypes.sizeof(JOYINFOEX)
            ji.dwFlags = JOY_RETURNALL
            res = self._winmm.joyGetPosEx(dev_id, ctypes.byref(ji))
            if res == JOYERR_NOERROR:
                self.device_id = dev_id
                self.connected = True

                caps = JOYCAPSW()
                c_res = self._winmm.joyGetDevCapsW(dev_id, ctypes.byref(caps), ctypes.sizeof(JOYCAPSW))
                if c_res == JOYERR_NOERROR:
                    self.device_name = str(caps.szPname).strip() or f"Joystick #{dev_id}"
                    self.num_axes = int(caps.wNumAxes)
                    self.num_buttons = int(caps.wNumButtons)
                else:
                    self.device_name = f"Joystick #{dev_id}"
                    self.num_axes = 6
                    self.num_buttons = 24

                # Enrich device name
                if "Microsoft" in self.device_name or "PC-joystick" in self.device_name or "HID" in self.device_name:
                    self.device_name = f"RadioMaster TX16S (USB Joystick HID)"

                return True

        self.connected = False
        self.device_name = "Not Connected"
        return False

    @staticmethod
    def _normalize_axis(raw_val: int, deadzone: float = 0.03, invert: bool = False) -> float:
        """Convert raw 0..65535 axis into [-1.0, 1.0] with deadzone."""
        norm = (float(raw_val) - 32767.5) / 32767.5
        norm = max(-1.0, min(1.0, norm))

        if abs(norm) < deadzone:
            norm = 0.0
        else:
            sign = 1.0 if norm > 0 else -1.0
            norm = sign * ((abs(norm) - deadzone) / (1.0 - deadzone))

        if invert:
            norm = -norm
        return float(norm)

    def read(self) -> Dict:
        """
        Poll joystick state.
        Returns:
            dict containing roll, pitch, throttle, yaw, buttons, events, raw axes, etc.
        """
        now = time.monotonic()
        if not self.connected and (now - self._last_scan_time > self._scan_interval):
            self.scan_and_connect()

        result = {
            "connected": False,
            "device_name": self.device_name,
            "device_id": self.device_id,
            "roll": 0.0,
            "pitch": 0.0,
            "throttle": 0.0,
            "yaw": 0.0,
            "raw_axes": {"X": 32767, "Y": 32767, "Z": 32767, "R": 32767, "U": 32767, "V": 32767},
            "norm_axes": {"X": 0.0, "Y": 0.0, "Z": 0.0, "R": 0.0, "U": 0.0, "V": 0.0},
            "buttons": [False] * 32,
            "pressed_buttons": set(),
            "released_buttons": set(),
            "switch_arm": None,
        }

        if not self.connected or self._winmm is None:
            return result

        ji = JOYINFOEX()
        ji.dwSize = ctypes.sizeof(JOYINFOEX)
        ji.dwFlags = JOY_RETURNALL

        res = self._winmm.joyGetPosEx(self.device_id, ctypes.byref(ji))
        if res != JOYERR_NOERROR:
            self.connected = False
            self.device_name = "Disconnected"
            return result

        result["connected"] = True
        result["device_name"] = self.device_name

        raw_map = {
            "X": int(ji.dwXpos),
            "Y": int(ji.dwYpos),
            "Z": int(ji.dwZpos),
            "R": int(ji.dwRpos),
            "U": int(ji.dwUpos),
            "V": int(ji.dwVpos),
        }
        result["raw_axes"] = raw_map

        # Normalized values of each physical axis [-1.0, 1.0] without inversion
        norm_map = {k: self._normalize_axis(v, self.deadzone, False) for k, v in raw_map.items()}
        result["norm_axes"] = norm_map

        # Map to flight channels with respective inversions
        val_pitch = raw_map.get(self.axis_pitch, 32767)
        val_roll = raw_map.get(self.axis_roll, 32767)
        val_thr = raw_map.get(self.axis_throttle, 32767)
        val_yaw = raw_map.get(self.axis_yaw, 32767)

        result["pitch"] = self._normalize_axis(val_pitch, self.deadzone, self.invert_pitch)
        result["roll"] = self._normalize_axis(val_roll, self.deadzone, self.invert_roll)
        result["throttle"] = self._normalize_axis(val_thr, self.deadzone, self.invert_throttle)
        result["yaw"] = self._normalize_axis(val_yaw, self.deadzone, self.invert_yaw)

        # Buttons (up to 32 buttons)
        cur_mask = ji.dwButtons
        buttons_list = []
        pressed_set = set()
        released_set = set()

        for b in range(32):
            bit = (cur_mask >> b) & 1
            is_down = bool(bit)
            buttons_list.append(is_down)

            last_bit = (self._last_buttons_mask >> b) & 1
            if bit and not last_bit:
                pressed_set.add(b)
            elif not bit and last_bit:
                released_set.add(b)

        self._last_buttons_mask = cur_mask
        result["buttons"] = buttons_list
        result["pressed_buttons"] = pressed_set
        result["released_buttons"] = released_set

        # Switch mapping (Button 0 -> SA/SF)
        if 0 in pressed_set:
            result["switch_arm"] = True
        elif 0 in released_set:
            result["switch_arm"] = False

        return result
