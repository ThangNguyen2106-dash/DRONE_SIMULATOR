"""MAVLink UDP connection for the drone simulator."""

import socket
from collections import deque
from typing import Optional, Tuple

from pymavlink import mavutil


class MAVLinkConnection:
    """
    UDP MAVLink endpoint for the simulated drone.

    The simulator acts as a MAVLink vehicle.

    Ground Station
          |
          | UDP MAVLink
          v
    MAVLinkConnection
          |
          v
    Drone Simulator

    RX:
        Receives MAVLink packets from the Ground Station.

    TX:
        Sends MAVLink telemetry/response packets to the
        Ground Station.

    The simulator uses one UDP socket for both RX and TX.
    """

    def __init__(
        self,
        connection_string: str = "udp:127.0.0.1:14550",
        source_system: int = 1,
        source_component: int = 1,
        rx_host: Optional[str] = None,
        rx_port: Optional[int] = None,
    ):

        self.connection_string = (
            connection_string
        )

        self.source_system = int(
            source_system
        )

        self.source_component = int(
            source_component
        )

        # ====================================================
        # Parse connection string
        # ====================================================

        (
            parsed_host,
            parsed_port,
        ) = self._parse_connection_string(
            connection_string
        )

        # ====================================================
        # REMOTE / DEFAULT TX
        # ====================================================

        self.tx_host = parsed_host

        self.tx_port = parsed_port

        self.tx_address = (
            self.tx_host,
            self.tx_port,
        )

        # ====================================================
        # LOCAL RX
        # ====================================================

        self.rx_host = (
            rx_host
            if rx_host is not None
            else "0.0.0.0"
        )

        self.rx_port = (
            int(rx_port)
            if rx_port is not None
            else parsed_port
        )

        self._validate_port(
            self.tx_port,
            "TX",
        )

        self._validate_port(
            self.rx_port,
            "RX",
        )

        # ====================================================
        # UDP SOCKET
        # ====================================================

        self.socket: Optional[
            socket.socket
        ] = None

        # Compatibility aliases
        self.tx_socket: Optional[
            socket.socket
        ] = None

        self.rx_socket: Optional[
            socket.socket
        ] = None

        # ====================================================
        # CONNECTION STATE
        # ====================================================

        self.connected = False

        # ====================================================
        # MAVLink parser / encoder
        # ====================================================

        self.mavlink = (
            mavutil.mavlink.MAVLink(
                None
            )
        )

        self.mavlink.srcSystem = (
            self.source_system
        )

        self.mavlink.srcComponent = (
            self.source_component
        )

        # ====================================================
        # RX MESSAGE QUEUE
        # ====================================================

        self._rx_message_queue = (
            deque()
        )

        # ====================================================
        # LAST GCS ADDRESS
        # ====================================================

        self.last_rx_address: Optional[
            Tuple[str, int]
        ] = None

        # ====================================================
        # STATISTICS
        # ====================================================

        self.tx_count = 0
        self.rx_count = 0

        self.tx_errors = 0
        self.rx_errors = 0

        self.parse_errors = 0

    # ========================================================
    # COMPATIBILITY API
    # ========================================================

    @property
    def connection(self):
        """
        Compatibility with existing project code.

        Allows:

            connection.connection.mav
        """

        return self

    # ========================================================

    @property
    def mav(self):
        """
        MAVLink encoder.

        Allows:

            connection.connection.mav.heartbeat_send(...)
        """

        return self.mavlink

    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def _validate_port(
        port: int,
        name: str,
    ):

        try:

            port = int(port)

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                f"Invalid MAVLink {name} port: "
                f"{port}"
            ) from exc

        if not (
            1
            <= port
            <= 65535
        ):

            raise ValueError(
                f"Invalid MAVLink {name} port: "
                f"{port}"
            )

    # ========================================================
    # PARSE CONNECTION STRING
    # ========================================================

    @staticmethod
    def _parse_connection_string(
        connection_string: str,
    ) -> Tuple[str, int]:

        if not connection_string:

            connection_string = (
                "udp:127.0.0.1:14550"
            )

        value = (
            str(
                connection_string
            ).strip()
        )

        # ----------------------------------------------------
        # Protocol
        # ----------------------------------------------------

        protocol = "udp"

        if ":" in value:

            possible_protocol, remainder = (
                value.split(
                    ":",
                    1,
                )
            )

            possible_protocol = (
                possible_protocol.lower()
            )

            if possible_protocol in (
                "udp",
                "udpout",
                "udpin",
            ):

                protocol = (
                    possible_protocol
                )

                value = remainder

        if protocol not in (
            "udp",
            "udpout",
            "udpin",
        ):

            raise ValueError(
                "Unsupported MAVLink protocol: "
                f"{protocol}"
            )

        # ----------------------------------------------------
        # HOST:PORT
        # ----------------------------------------------------

        parts = value.rsplit(
            ":",
            1,
        )

        if len(parts) != 2:

            raise ValueError(
                "Invalid MAVLink connection "
                f"string: {connection_string}"
            )

        host = (
            parts[0].strip()
        )

        if not host:

            host = "127.0.0.1"

        try:

            port = int(
                parts[1]
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                "Invalid MAVLink port: "
                f"{parts[1]}"
            ) from exc

        if not (
            1
            <= port
            <= 65535
        ):

            raise ValueError(
                f"Invalid MAVLink port: {port}"
            )

        return (
            host,
            port,
        )

    # ========================================================
    # CONNECT
    # ========================================================

    def connect(self):

        if self.connected:

            return

        # ----------------------------------------------------
        # Create UDP socket
        # ----------------------------------------------------

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        # ----------------------------------------------------
        # Bind simulator RX endpoint
        # ----------------------------------------------------

        try:

            sock.bind(
                (
                    self.rx_host,
                    self.rx_port,
                )
            )

        except OSError:

            try:

                sock.close()

            except Exception:

                pass

            raise

        # ----------------------------------------------------
        # Non-blocking
        # ----------------------------------------------------

        sock.setblocking(
            False
        )

        # ----------------------------------------------------
        # Save socket
        # ----------------------------------------------------

        self.socket = sock

        self.tx_socket = sock

        self.rx_socket = sock

        # ----------------------------------------------------
        # Reset runtime state
        # ----------------------------------------------------

        self._rx_message_queue.clear()

        self.last_rx_address = None

        self.connected = True

        # ----------------------------------------------------
        # Log
        # ----------------------------------------------------

        print(
            "======================================"
        )

        print(
            "[MAVLINK] UDP endpoint established"
        )

        print(
            f"[MAVLINK] Local RX: "
            f"{self.rx_host}:{self.rx_port}"
        )

        print(
            f"[MAVLINK] Default TX: "
            f"{self.tx_host}:{self.tx_port}"
        )

        print(
            f"[MAVLINK] SYSID="
            f"{self.source_system} "
            f"COMPID="
            f"{self.source_component}"
        )

        print(
            "======================================"
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.connected = False

        sock = self.socket

        self.socket = None

        self.tx_socket = None

        self.rx_socket = None

        self.last_rx_address = None

        self._rx_message_queue.clear()

        if sock is not None:

            try:

                sock.close()

            except Exception:

                pass

        print(
            "[MAVLINK] Connection closed"
        )

    # ========================================================
    # SEND MAVLINK MESSAGE
    # ========================================================

    def send(
        self,
        message,
        address=None,
    ) -> bool:
        """
        Encode and send one MAVLink message.

        Destination priority:

        1. Explicit address.
        2. Last address from which a GCS packet arrived.
        3. Configured default TX address.
        """

        if not self.connected:

            return False

        if self.socket is None:

            return False

        if message is None:

            return False

        try:

            # ------------------------------------------------
            # Encode
            # ------------------------------------------------

            packet = message.pack(
                self.mavlink
            )

            if not packet:

                return False

            # ------------------------------------------------
            # Destination
            # ------------------------------------------------

            destination = (
                address
                if address is not None
                else (
                    self.last_rx_address
                    or self.tx_address
                )
            )

            # ------------------------------------------------
            # Send
            # ------------------------------------------------

            sent = self.socket.sendto(
                packet,
                destination,
            )

            if sent != len(packet):

                self.tx_errors += 1

                print(
                    "[MAVLINK TX ERROR] "
                    "Incomplete UDP packet"
                )

                return False

            self.tx_count += 1

            return True

        except Exception as exc:

            self.tx_errors += 1

            print(
                "[MAVLINK TX ERROR] "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return False

    # ========================================================
    # RECEIVE
    # ========================================================

    def receive(
        self,
        blocking=False,
        timeout=0.0,
    ):
        """
        Receive one MAVLink message.

        blocking=False:
            Return immediately if no message exists.

        blocking=True:
            Wait for a UDP packet until timeout.
        """

        if not self.connected:

            return None

        if self.socket is None:

            return None

        # ----------------------------------------------------
        # Already parsed messages
        # ----------------------------------------------------

        if self._rx_message_queue:

            return (
                self._rx_message_queue.popleft()
            )

        # ====================================================
        # BLOCKING
        # ====================================================

        if blocking:

            try:

                if (
                    timeout is not None
                    and timeout > 0
                ):

                    self.socket.settimeout(
                        float(timeout)
                    )

                else:

                    self.socket.settimeout(
                        None
                    )

                data, address = (
                    self.socket.recvfrom(
                        65535
                    )
                )

                self.last_rx_address = (
                    address
                )

                self._parse_packet(
                    data,
                    address,
                )

                if self._rx_message_queue:

                    return (
                        self._rx_message_queue.popleft()
                    )

                return None

            except socket.timeout:

                return None

            except Exception as exc:

                self.rx_errors += 1

                print(
                    "[MAVLINK RX ERROR] "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                return None

            finally:

                try:

                    self.socket.setblocking(
                        False
                    )

                except Exception:

                    pass

        # ====================================================
        # NON-BLOCKING
        # ====================================================

        try:

            data, address = (
                self.socket.recvfrom(
                    65535
                )
            )

            self.last_rx_address = (
                address
            )

            self._parse_packet(
                data,
                address,
            )

            if self._rx_message_queue:

                return (
                    self._rx_message_queue.popleft()
                )

            return None

        except BlockingIOError:

            return None

        except socket.timeout:

            return None

        except ConnectionResetError:

            # Windows UDP:
            # Remote endpoint may have closed / rejected the port.
            # This is not a fatal simulator error.
            return None

        except OSError as exc:

            # Windows may report UDP connection reset as WinError 10054.
            if getattr(exc, "winerror", None) == 10054:

                return None

            self.rx_errors += 1

            print(
                "[MAVLINK RX ERROR] "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return None

        except Exception as exc:

            self.rx_errors += 1

            print(
                "[MAVLINK RX ERROR] "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return None

    # ========================================================
    # PARSE PACKET
    # ========================================================

    def _parse_packet(
        self,
        data,
        address=None,
    ) -> int:
        """
        Parse all MAVLink frames contained in one UDP packet.
        """

        if not data:

            return 0

        parsed_count = 0

        for byte in data:

            try:

                message = (
                    self.mavlink.parse_char(
                        bytes([byte])
                    )
                )

            except Exception as exc:

                self.parse_errors += 1

                print(
                    "[MAVLINK PARSE ERROR] "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                continue

            if message is not None:

                self._rx_message_queue.append(
                    message
                )

                self.rx_count += 1

                parsed_count += 1

        return parsed_count

    # ========================================================
    # RECEIVE ALL
    # ========================================================

    def receive_all(
        self,
        max_messages=100,
    ):
        """
        Receive all currently available messages.
        """

        messages = []

        if not self.connected:

            return messages

        if self.socket is None:

            return messages

        try:

            max_messages = int(
                max_messages
            )

        except (
            TypeError,
            ValueError,
        ):

            max_messages = 100

        max_messages = max(
            1,
            max_messages,
        )

        # ----------------------------------------------------
        # Drain queue
        # ----------------------------------------------------

        while (
            self._rx_message_queue
            and
            len(messages)
            < max_messages
        ):

            messages.append(
                self._rx_message_queue.popleft()
            )

        # ----------------------------------------------------
        # Read UDP packets
        # ----------------------------------------------------

        while (
            len(messages)
            < max_messages
        ):

            message = self.receive(
                blocking=False
            )

            if message is None:

                break

            messages.append(
                message
            )

        return messages

    # ========================================================
    # FLUSH RX
    # ========================================================

    def flush_rx(self):

        self._rx_message_queue.clear()

        if self.socket is None:

            return

        while True:

            try:

                self.socket.recvfrom(
                    65535
                )

            except (
                BlockingIOError,
                socket.timeout,
            ):

                break

            except Exception:

                break

    # ========================================================
    # SEND RAW
    # ========================================================

    def send_raw(
        self,
        packet: bytes,
        address=None,
    ) -> bool:

        if not self.connected:

            return False

        if self.socket is None:

            return False

        if not packet:

            return False

        try:

            destination = (
                address
                if address is not None
                else (
                    self.last_rx_address
                    or self.tx_address
                )
            )

            sent = self.socket.sendto(
                packet,
                destination,
            )

            if sent != len(packet):

                self.tx_errors += 1

                return False

            self.tx_count += 1

            return True

        except Exception as exc:

            self.tx_errors += 1

            print(
                "[MAVLINK TX ERROR] "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            return False

    # ========================================================
    # STATUS
    # ========================================================

    def is_connected(self) -> bool:

        return bool(
            self.connected
            and self.socket is not None
        )

    # ========================================================
    # STATISTICS
    # ========================================================

    def get_statistics(self):

        return {
            "connected":
                self.connected,

            "local_rx_host":
                self.rx_host,

            "local_rx_port":
                self.rx_port,

            "remote_tx_host":
                self.tx_host,

            "remote_tx_port":
                self.tx_port,

            "last_rx_address":
                self.last_rx_address,

            "tx_count":
                self.tx_count,

            "rx_count":
                self.rx_count,

            "tx_errors":
                self.tx_errors,

            "rx_errors":
                self.rx_errors,

            "parse_errors":
                self.parse_errors,

            "queued_messages":
                len(
                    self._rx_message_queue
                ),
        }

    # ========================================================
    # CONTEXT MANAGER
    # ========================================================

    def __enter__(self):

        self.connect()

        return self

    # ========================================================

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        self.close()