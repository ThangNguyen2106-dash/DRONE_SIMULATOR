from PySide6.QtWidgets import (
    QGroupBox,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
)


class MAVLinkConfigPanel(QGroupBox):

    def __init__(self, parent=None):
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

        # Hiện tại simulator chỉ dùng UDP.
        self.connection_type.addItem(
            "UDP"
        )

        layout.addRow(
            "Connection Type:",
            self.connection_type,
        )

        # ====================================================
        # IP ADDRESS
        # ====================================================

        self.ip_address = QLineEdit()

        self.ip_address.setText(
            "127.0.0.1"
        )

        self.ip_address.setPlaceholderText(
            "127.0.0.1"
        )

        layout.addRow(
            "IP Address:",
            self.ip_address,
        )

        # ====================================================
        # PORT
        # ====================================================

        self.port = QSpinBox()

        self.port.setRange(
            1,
            65535,
        )

        self.port.setValue(
            14550
        )

        layout.addRow(
            "Port:",
            self.port,
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

        self.telemetry_rate = QDoubleSpinBox()

        self.telemetry_rate.setDecimals(
            1
        )

        self.telemetry_rate.setRange(
            1.0,
            100.0,
        )

        self.telemetry_rate.setSingleStep(
            1.0
        )

        self.telemetry_rate.setSuffix(
            " Hz"
        )

        self.telemetry_rate.setValue(
            20.0
        )

        layout.addRow(
            "Telemetry Rate:",
            self.telemetry_rate,
        )

        self.setLayout(
            layout
        )

    # ========================================================
    # GET CONFIG
    # ========================================================

    def get_config(self):

        ip_address = (
            self.ip_address.text().strip()
        )

        if not ip_address:
            ip_address = "127.0.0.1"

        port = self.port.value()

        system_id = (
            self.system_id.value()
        )

        component_id = (
            self.component_id.value()
        )

        telemetry_rate = (
            self.telemetry_rate.value()
        )

        # ----------------------------------------------------
        # UDP
        # ----------------------------------------------------

        connection_string = (
            f"udp:0.0.0.0:{port}"
        )

        return {
            "connection_type": "UDP",

            "ip_address": ip_address,

            "port": port,

            "system_id": system_id,

            "component_id": component_id,

            "telemetry_rate": telemetry_rate,

            "connection_string": connection_string,
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

        self.ip_address.setEnabled(
            enabled
        )

        self.port.setEnabled(
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