"""
MAVLink connection layer.

Responsible for:
- Creating MAVLink UDP/serial connection
- Sending MAVLink packets
- Receiving MAVLink packets
"""

from typing import Optional

from pymavlink import mavutil


class MAVLinkConnection:

    def __init__(
        self,
        connection_string: str = "udpout:127.0.0.1:14550",
        source_system: int = 1,
        source_component: int = 1,
    ):

        self.connection_string = connection_string

        self.source_system = source_system
        self.source_component = source_component

        self.connection: Optional[
            mavutil.mavfile
        ] = None

    # ========================================================
    # CONNECT
    # ========================================================

    def connect(self) -> None:

        if self.connection is not None:
            return

        self.connection = mavutil.mavlink_connection(
            self.connection_string,
            source_system=self.source_system,
            source_component=self.source_component,
        )

        print(
            f"[MAVLINK] Connected: "
            f"{self.connection_string}"
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self) -> None:

        if self.connection is None:
            return

        try:
            self.connection.close()
        except Exception:
            pass

        self.connection = None

        print("[MAVLINK] Connection closed")

    # ========================================================
    # SEND
    # ========================================================

    def send(self, message) -> bool:

        if self.connection is None:
            return False

        try:

            self.connection.mav.send(
                message
            )

            return True

        except Exception as exc:

            print(
                f"[MAVLINK ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            return False

    # ========================================================
    # RECEIVE
    # ========================================================

    def receive(
        self,
        blocking: bool = False,
        timeout: float = 0.0,
    ):

        if self.connection is None:
            return None

        try:

            return self.connection.recv_match(
                blocking=blocking,
                timeout=timeout,
            )

        except Exception as exc:

            print(
                f"[MAVLINK RX ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            return None