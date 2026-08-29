"""
Centralized MAVLink debug logger.

Design goals
------------
The simulator currently scatters raw ``print("[MAVLINK] ...")`` calls
across connection.py / telemetry.py / *_receiver.py. That makes it
impossible for a teammate to:

  - turn noisy channels (e.g. every RX/TX packet) on/off independently
  - tell at a glance whether a line is informational, a warning, or an
    actual failure
  - grep logs by category ("CONN", "TX", "RX", "PARSE", "MISSION", ...)
  - get consistent timestamps or redirect output to a file

This module gives every MAVLink component ONE logger with:

  - Levels: DEBUG < INFO < WARN < ERROR (like standard logging)
  - Categories: independent on/off switches so you can e.g. watch only
    RX + PARSE while debugging a "GCS not receiving heartbeat" issue.
  - A consistent line format:
        HH:MM:SS.mmm [LEVEL][CATEGORY] message
  - Optional mirroring to a rotating log file for post-mortem debugging.

Usage
-----
    from mavlink.mav_logger import mav_log

    mav_log.info("CONN", "UDP endpoint established")
    mav_log.debug("TX", f"HEARTBEAT sysid={sysid}")
    mav_log.warn("RX", "unexpected component id")
    mav_log.error("PARSE", f"bad buffer: {exc}")

Runtime control (e.g. from a GUI debug panel or console):

    mav_log.set_level("DEBUG")            # show everything
    mav_log.enable_category("RX")
    mav_log.disable_category("TX")        # silence noisy TX spam
    mav_log.enable_file_logging("mavlink_debug.log")
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, Optional


# ============================================================
# LEVELS
# ============================================================

LEVEL_DEBUG = 10
LEVEL_INFO = 20
LEVEL_WARN = 30
LEVEL_ERROR = 40

_LEVEL_NAMES = {
    LEVEL_DEBUG: "DEBUG",
    LEVEL_INFO: "INFO",
    LEVEL_WARN: "WARN",
    LEVEL_ERROR: "ERROR",
}

_NAME_TO_LEVEL = {name: level for level, name in _LEVEL_NAMES.items()}

# ANSI colors (safe no-op on terminals that don't support them)
_LEVEL_COLORS = {
    LEVEL_DEBUG: "\033[90m",   # gray
    LEVEL_INFO: "\033[36m",    # cyan
    LEVEL_WARN: "\033[33m",    # yellow
    LEVEL_ERROR: "\033[31m",   # red
}
_COLOR_RESET = "\033[0m"

# ============================================================
# CATEGORIES
#
# One switch per subsystem so a teammate debugging e.g. mission
# upload issues can do:
#
#   mav_log.only(["MISSION", "RX"])
#
# and not be drowned in ATTITUDE/GPS telemetry spam.
# ============================================================

CONN = "CONN"          # connect/disconnect/socket lifecycle
TX = "TX"               # outgoing telemetry messages
RX = "RX"               # incoming GCS messages
PARSE = "PARSE"         # MAVLink buffer parsing
MISSION = "MISSION"     # mission upload/download/progress
COMMAND = "COMMAND"     # COMMAND_LONG / COMMAND_INT handling
HEARTBEAT = "HEARTBEAT"  # heartbeat specific (very high volume)

ALL_CATEGORIES = [
    CONN,
    TX,
    RX,
    PARSE,
    MISSION,
    COMMAND,
    HEARTBEAT,
]


class MavLogger:
    """
    Single shared logger instance for the whole mavlink package.

    Not thread-safe beyond what plain print()/file writes already are
    (the simulator's MAVLink I/O all happens on one thread/tick loop).
    """

    def __init__(self):

        self.level = LEVEL_INFO

        # Every category is ON by default so behavior matches the old
        # "everything prints" state until a teammate narrows it down.
        self.enabled_categories: Dict[str, bool] = {
            category: True for category in ALL_CATEGORIES
        }

        # sys.stdout is None in a windowed/noconsole PyInstaller
        # build (no console attached), which would crash
        # .isatty() right here at import time.
        self.use_color = (
            sys.stdout is not None
            and sys.stdout.isatty()
        )

        self._file = None
        self._file_path: Optional[str] = None

        # Rate limiting: category -> (last_emit_monotonic, min_interval)
        self._rate_limits: Dict[str, float] = {}
        self._last_emit: Dict[str, float] = {}

    # ========================================================
    # LEVEL CONTROL
    # ========================================================

    def set_level(self, level) -> None:
        """Accepts either an int (LEVEL_*) or a name ("DEBUG", "INFO", ...)."""

        if isinstance(level, str):
            level = _NAME_TO_LEVEL.get(level.upper(), LEVEL_INFO)

        self.level = level

    # ========================================================
    # CATEGORY CONTROL
    # ========================================================

    def enable_category(self, category: str) -> None:
        self.enabled_categories[category] = True

    def disable_category(self, category: str) -> None:
        self.enabled_categories[category] = False

    def only(self, categories) -> None:
        """Enable exactly the given categories, disable everything else."""

        wanted = set(categories)

        for category in ALL_CATEGORIES:
            self.enabled_categories[category] = category in wanted

    def enable_all(self) -> None:

        for category in ALL_CATEGORIES:
            self.enabled_categories[category] = True

    # ========================================================
    # RATE LIMITING
    #
    # High-frequency categories (TX at 20Hz, HEARTBEAT at 1Hz but
    # noisy per-run) can be capped so the console stays readable
    # without disabling the category entirely.
    # ========================================================

    def set_rate_limit(self, category: str, min_interval_seconds: float) -> None:
        self._rate_limits[category] = float(min_interval_seconds)

    def clear_rate_limit(self, category: str) -> None:
        self._rate_limits.pop(category, None)
        self._last_emit.pop(category, None)

    def _rate_limited(self, category: str) -> bool:

        interval = self._rate_limits.get(category)

        if interval is None:
            return False

        now = time.monotonic()
        last = self._last_emit.get(category, 0.0)

        if now - last < interval:
            return True

        self._last_emit[category] = now
        return False

    # ========================================================
    # FILE LOGGING
    # ========================================================

    def enable_file_logging(self, path: str) -> None:

        self.disable_file_logging()

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        self._file = open(file_path, "a", encoding="utf-8")
        self._file_path = str(file_path)

        self._file.write(
            f"\n===== MAVLink debug log started "
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} =====\n"
        )
        self._file.flush()

    def disable_file_logging(self) -> None:

        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass

        self._file = None
        self._file_path = None

    # ========================================================
    # CORE EMIT
    # ========================================================

    def _emit(self, level: int, category: str, message: str) -> None:

        if level < self.level:
            return

        if not self.enabled_categories.get(category, True):
            return

        if self._rate_limited(category):
            return

        timestamp = time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"

        level_name = _LEVEL_NAMES.get(level, "INFO")

        line = f"{timestamp} [{level_name}][{category}] {message}"

        if self.use_color:
            color = _LEVEL_COLORS.get(level, "")
            print(f"{color}{line}{_COLOR_RESET}")
        else:
            print(line)

        if self._file is not None:
            try:
                self._file.write(line + "\n")
                self._file.flush()
            except Exception:
                pass

    # ========================================================
    # PUBLIC API
    # ========================================================

    def debug(self, category: str, message: str) -> None:
        self._emit(LEVEL_DEBUG, category, message)

    def info(self, category: str, message: str) -> None:
        self._emit(LEVEL_INFO, category, message)

    def warn(self, category: str, message: str) -> None:
        self._emit(LEVEL_WARN, category, message)

    def error(self, category: str, message: str) -> None:
        self._emit(LEVEL_ERROR, category, message)


# ============================================================
# SHARED SINGLETON
#
# Import this everywhere instead of constructing MavLogger()
# so runtime toggles (set_level, only, enable_file_logging, ...)
# apply consistently across connection.py / telemetry.py /
# command_receiver.py / mission_receiver.py.
# ============================================================

mav_log = MavLogger()
