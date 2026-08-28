from PySide6.QtWidgets import (
    QGroupBox,
    QFormLayout,
    QDoubleSpinBox,
)


class DroneConfigPanel(QGroupBox):

    def __init__(self, parent=None):

        super().__init__(
            "DRONE CONFIGURATION",
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
        # LATITUDE
        # ====================================================

        self.latitude = QDoubleSpinBox()

        self.latitude.setDecimals(
            7
        )

        self.latitude.setRange(
            -90.0,
            90.0,
        )

        self.latitude.setSingleStep(
            0.0001
        )

        self.latitude.setValue(
            10.8231000
        )

        layout.addRow(
            "Latitude:",
            self.latitude,
        )

        # ====================================================
        # LONGITUDE
        # ====================================================

        self.longitude = QDoubleSpinBox()

        self.longitude.setDecimals(
            7
        )

        self.longitude.setRange(
            -180.0,
            180.0,
        )

        self.longitude.setSingleStep(
            0.0001
        )

        self.longitude.setValue(
            106.6297000
        )

        layout.addRow(
            "Longitude:",
            self.longitude,
        )

        # ====================================================
        # START ALTITUDE
        # ====================================================

        self.start_altitude = QDoubleSpinBox()

        self.start_altitude.setDecimals(
            2
        )

        self.start_altitude.setRange(
            0.0,
            10000.0,
        )

        self.start_altitude.setSingleStep(
            1.0
        )

        self.start_altitude.setSuffix(
            " m"
        )

        self.start_altitude.setValue(
            0.0
        )

        layout.addRow(
            "Start Altitude:",
            self.start_altitude,
        )

        # ====================================================
        # TAKEOFF ALTITUDE
        # ====================================================

        self.takeoff_altitude = QDoubleSpinBox()

        self.takeoff_altitude.setDecimals(
            2
        )

        self.takeoff_altitude.setRange(
            0.0,
            10000.0,
        )

        self.takeoff_altitude.setSingleStep(
            1.0
        )

        self.takeoff_altitude.setSuffix(
            " m"
        )

        self.takeoff_altitude.setValue(
            20.0
        )

        layout.addRow(
            "Takeoff Altitude:",
            self.takeoff_altitude,
        )

        # ====================================================
        # SPEED
        # ====================================================

        self.speed = QDoubleSpinBox()

        self.speed.setDecimals(
            2
        )

        self.speed.setRange(
            0.0,
            100.0,
        )

        self.speed.setSingleStep(
            0.5
        )

        self.speed.setSuffix(
            " m/s"
        )

        self.speed.setValue(
            5.0
        )

        layout.addRow(
            "Speed:",
            self.speed,
        )

        # ====================================================
        # HEADING
        # ====================================================

        self.heading = QDoubleSpinBox()

        self.heading.setDecimals(
            2
        )

        self.heading.setRange(
            0.0,
            359.99,
        )

        self.heading.setSingleStep(
            5.0
        )

        self.heading.setSuffix(
            " °"
        )

        self.heading.setValue(
            90.0
        )

        layout.addRow(
            "Heading:",
            self.heading,
        )

        self.setLayout(
            layout
        )

    # ========================================================
    # GET CONFIG
    # ========================================================

    def get_config(self):

        return {
            "lat": self.latitude.value(),

            "lon": self.longitude.value(),

            "alt": self.start_altitude.value(),

            "takeoff_altitude":
                self.takeoff_altitude.value(),

            "speed": self.speed.value(),

            "heading": self.heading.value(),
        }

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(
        self,
        enabled,
    ):

        self.latitude.setEnabled(
            enabled
        )

        self.longitude.setEnabled(
            enabled
        )

        self.start_altitude.setEnabled(
            enabled
        )

        self.takeoff_altitude.setEnabled(
            enabled
        )

        self.speed.setEnabled(
            enabled
        )

        self.heading.setEnabled(
            enabled
        )