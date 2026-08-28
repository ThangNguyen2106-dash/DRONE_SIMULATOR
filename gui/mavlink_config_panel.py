from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QLabel,
)


class MAVLinkConfigPanel(QGroupBox):

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        parent=None,
    ):

        super().__init__(
            "MAVLINK CONFIGURATION",
            parent,
        )

        self._setup_ui()

    # ========================================================
    # UI
    # ========================================================

    def _setup_ui(self):

        layout = QFormLayout()

        layout.setContentsMargins(
            15,
            15,
            15,
            15,
        )

        layout.setSpacing(
            10
        )

        # ====================================================
        # CONNECTION TYPE
        # ====================================================

        self.connection_type = QComboBox()

        self.connection_type.addItems([
            "UDP",
            "TCP",
            "SERIAL",
        ])

        self.connection_type.currentTextChanged.connect(
            self._on_connection_type_changed
        )

        layout.addRow(
            "Connection Type:",
            self.connection_type,
        )

        # ====================================================
        # TX HOST
        # ====================================================

        self.tx_host = QLineEdit()

        self.tx_host.setText(
            "127.0.0.1"
        )

        self.tx_host.setPlaceholderText(
            "127.0.0.1"
        )

        layout.addRow(
            "TX Host:",
            self.tx_host,
        )

        # ====================================================
        # TX PORT
        # ====================================================

        self.tx_port = QSpinBox()

        self.tx_port.setRange(
            1,
            65535,
        )

        self.tx_port.setValue(
            14550
        )

        layout.addRow(
            "TX Port:",
            self.tx_port,
        )

        # ====================================================
        # RX HOST
        # ====================================================

        self.rx_host = QLineEdit()

        self.rx_host.setText(
            "0.0.0.0"
        )

        self.rx_host.setPlaceholderText(
            "0.0.0.0"
        )

        layout.addRow(
            "RX Host:",
            self.rx_host,
        )

        # ====================================================
        # RX PORT
        # ====================================================

        self.rx_port = QSpinBox()

        self.rx_port.setRange(
            1,
            65535,
        )

        self.rx_port.setValue(
            14560
        )

        layout.addRow(
            "RX Port:",
            self.rx_port,
        )

        # ====================================================
        # SERIAL DEVICE
        # ====================================================

        self.serial_device = QLineEdit()

        self.serial_device.setText(
            "COM3"
        )

        self.serial_device.setPlaceholderText(
            "COM3"
        )

        layout.addRow(
            "Serial Device:",
            self.serial_device,
        )

        # ====================================================
        # BAUDRATE
        # ====================================================

        self.baudrate = QSpinBox()

        self.baudrate.setRange(
            1200,
            4000000,
        )

        self.baudrate.setValue(
            115200
        )

        layout.addRow(
            "Baudrate:",
            self.baudrate,
        )

        # ====================================================
        # SYSTEM ID
        # ====================================================

        self.system_id = QSpinBox()

        self.system_id.setRange(
            1,
            255,
        )

        self.system_id.setValue(
            1
        )

        layout.addRow(
            "System ID:",
            self.system_id,
        )

        # ====================================================
        # COMPONENT ID
        # ====================================================

        self.component_id = QSpinBox()

        self.component_id.setRange(
            1,
            255,
        )

        self.component_id.setValue(
            1
        )

        layout.addRow(
            "Component ID:",
            self.component_id,
        )

        # ====================================================
        # TELEMETRY RATE
        # ====================================================

        self.telemetry_rate = (
            QDoubleSpinBox()
        )

        self.telemetry_rate.setRange(
            0.1,
            200.0,
        )

        self.telemetry_rate.setDecimals(
            1
        )

        self.telemetry_rate.setSingleStep(
            1.0
        )

        self.telemetry_rate.setValue(
            20.0
        )

        self.telemetry_rate.setSuffix(
            " Hz"
        )

        layout.addRow(
            "Telemetry Rate:",
            self.telemetry_rate,
        )

        # ====================================================
        # MAVLINK VERSION
        # ====================================================

        self.mavlink_version = QComboBox()

        self.mavlink_version.addItems([
            "AUTO",
            "MAVLink 1",
            "MAVLink 2",
        ])

        self.mavlink_version.setCurrentText(
            "MAVLink 2"
        )

        layout.addRow(
            "MAVLink Version:",
            self.mavlink_version,
        )

        # ====================================================
        # TARGET SYSTEM
        # ====================================================

        self.target_system = QSpinBox()

        self.target_system.setRange(
            0,
            255,
        )

        self.target_system.setValue(
            0
        )

        layout.addRow(
            "Target System:",
            self.target_system,
        )

        # ====================================================
        # TARGET COMPONENT
        # ====================================================

        self.target_component = QSpinBox()

        self.target_component.setRange(
            0,
            255,
        )

        self.target_component.setValue(
            0
        )

        layout.addRow(
            "Target Component:",
            self.target_component,
        )

        # ====================================================
        # CONNECTION STRING
        # ====================================================

        self.connection_string = QLineEdit()

        self.connection_string.setPlaceholderText(
            "Generated automatically"
        )

        self.connection_string.setReadOnly(
            True
        )

        layout.addRow(
            "Connection String:",
            self.connection_string,
        )

        # ====================================================
        # STATUS
        # ====================================================

        self.config_status = QLabel(
            "UDP configuration"
        )

        self.config_status.setStyleSheet(
            """
            QLabel {
                padding: 4px;
            }
            """
        )

        layout.addRow(
            "Status:",
            self.config_status,
        )

        self.setLayout(
            layout
        )

        # ====================================================
        # INITIAL UPDATE
        # ====================================================

        self._update_connection_string()

    # ========================================================
    # CONNECTION TYPE
    # ========================================================

    def _on_connection_type_changed(
        self,
        connection_type,
    ):

        connection_type = str(
            connection_type
        ).upper()

        is_serial = (
            connection_type
            == "SERIAL"
        )

        # ----------------------------------------------------
        # UDP / TCP
        # ----------------------------------------------------

        self.tx_host.setEnabled(
            not is_serial
        )

        self.tx_port.setEnabled(
            not is_serial
        )

        self.rx_host.setEnabled(
            connection_type
            == "UDP"
        )

        self.rx_port.setEnabled(
            connection_type
            == "UDP"
        )

        # ----------------------------------------------------
        # Serial
        # ----------------------------------------------------

        self.serial_device.setEnabled(
            is_serial
        )

        self.baudrate.setEnabled(
            is_serial
        )

        self._update_connection_string()

    # ========================================================
    # UPDATE CONNECTION STRING
    # ========================================================

    def _update_connection_string(
        self,
    ):

        connection_type = (
            self.connection_type
            .currentText()
            .upper()
        )

        # ====================================================
        # UDP
        # ====================================================

        if connection_type == "UDP":

            host = (
                self.tx_host
                .text()
                .strip()
            )

            if not host:

                host = "127.0.0.1"

            port = (
                self.tx_port.value()
            )

            connection_string = (
                f"udpout:{host}:{port}"
            )

            self.connection_string.setText(
                connection_string
            )

            self.config_status.setText(
                "UDP TX/RX configuration"
            )

            return

        # ====================================================
        # TCP
        # ====================================================

        if connection_type == "TCP":

            host = (
                self.tx_host
                .text()
                .strip()
            )

            if not host:

                host = "127.0.0.1"

            port = (
                self.tx_port.value()
            )

            connection_string = (
                f"tcp:{host}:{port}"
            )

            self.connection_string.setText(
                connection_string
            )

            self.config_status.setText(
                "TCP configuration"
            )

            return

        # ====================================================
        # SERIAL
        # ====================================================

        if connection_type == "SERIAL":

            device = (
                self.serial_device
                .text()
                .strip()
            )

            if not device:

                device = "COM3"

            baudrate = (
                self.baudrate.value()
            )

            connection_string = (
                f"{device}:{baudrate}"
            )

            self.connection_string.setText(
                connection_string
            )

            self.config_status.setText(
                "Serial configuration"
            )

            return

    # ========================================================
    # GET CONFIG
    # ========================================================

    def get_config(
        self,
    ):

        connection_type = (
            self.connection_type
            .currentText()
            .strip()
            .upper()
        )

        tx_host = (
            self.tx_host
            .text()
            .strip()
        )

        if not tx_host:

            tx_host = "127.0.0.1"

        rx_host = (
            self.rx_host
            .text()
            .strip()
        )

        if not rx_host:

            rx_host = "0.0.0.0"

        tx_port = (
            self.tx_port.value()
        )

        rx_port = (
            self.rx_port.value()
        )

        system_id = (
            self.system_id.value()
        )

        component_id = (
            self.component_id.value()
        )

        telemetry_rate = (
            self.telemetry_rate.value()
        )

        serial_device = (
            self.serial_device
            .text()
            .strip()
        )

        if not serial_device:

            serial_device = "COM3"

        baudrate = (
            self.baudrate.value()
        )

        mavlink_version = (
            self.mavlink_version
            .currentText()
        )

        target_system = (
            self.target_system.value()
        )

        target_component = (
            self.target_component.value()
        )

        # ====================================================
        # CONNECTION STRING
        # ====================================================

        if connection_type == "UDP":

            connection_string = (
                f"udpout:"
                f"{tx_host}:"
                f"{tx_port}"
            )

        elif connection_type == "TCP":

            connection_string = (
                f"tcp:"
                f"{tx_host}:"
                f"{tx_port}"
            )

        elif connection_type == "SERIAL":

            connection_string = (
                f"{serial_device}:"
                f"{baudrate}"
            )

        else:

            connection_string = ""

        return {

            # =================================================
            # TYPE
            # =================================================

            "connection_type":
                connection_type,

            # =================================================
            # TX
            # =================================================

            "tx_host":
                tx_host,

            "tx_port":
                tx_port,

            # =================================================
            # RX
            # =================================================

            "rx_host":
                rx_host,

            "rx_port":
                rx_port,

            # =================================================
            # LEGACY
            # =================================================

            "ip_address":
                tx_host,

            "port":
                tx_port,

            # =================================================
            # MAVLINK IDs
            # =================================================

            "system_id":
                system_id,

            "component_id":
                component_id,

            "target_system":
                target_system,

            "target_component":
                target_component,

            # =================================================
            # SERIAL
            # =================================================

            "serial_device":
                serial_device,

            "baudrate":
                baudrate,

            # =================================================
            # TELEMETRY
            # =================================================

            "telemetry_rate":
                telemetry_rate,

            "telemetry_rate_hz":
                telemetry_rate,

            # =================================================
            # MAVLINK VERSION
            # =================================================

            "mavlink_version":
                mavlink_version,

            # =================================================
            # CONNECTION STRING
            # =================================================

            "connection_string":
                connection_string,
        }

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(
        self,
        enabled,
    ):

        self.connection_type.setEnabled(
            enabled
        )

        self.tx_host.setEnabled(
            enabled
        )

        self.tx_port.setEnabled(
            enabled
        )

        self.rx_host.setEnabled(
            enabled
        )

        self.rx_port.setEnabled(
            enabled
        )

        self.serial_device.setEnabled(
            enabled
        )

        self.baudrate.setEnabled(
            enabled
        )

        self.system_id.setEnabled(
            enabled
        )

        self.component_id.setEnabled(
            enabled
        )

        self.telemetry_rate.setEnabled(
            enabled
        )

        self.mavlink_version.setEnabled(
            enabled
        )

        self.target_system.setEnabled(
            enabled
        )

        self.target_component.setEnabled(
            enabled
        )

        # ----------------------------------------------------
        # Re-apply connection type rules.
        # ----------------------------------------------------

        if enabled:

            self._on_connection_type_changed(
                self.connection_type.currentText()
            )