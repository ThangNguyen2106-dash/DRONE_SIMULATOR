from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QSlider,
    QGroupBox,
    QScrollArea,
)

from gui.simulation_worker import SimulationWorker
from gui.drone_config_panel import DroneConfigPanel
from gui.mavlink_config_panel import MAVLinkConfigPanel


class MainWindow(QMainWindow):

    # ========================================================
    # INIT
    # ========================================================

    def __init__(self):

        super().__init__()

        # ====================================================
        # WINDOW
        # ====================================================

        self.setWindowTitle(
            "RIGEL UAV Simulator"
        )

        self.setMinimumSize(
            1200,
            850,
        )

        # ====================================================
        # WORKER
        # ====================================================

        self.worker = None

        # ====================================================
        # UI
        # ====================================================

        self._setup_ui()

    # ========================================================
    # SETUP UI
    # ========================================================

    def _setup_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        root_layout = QVBoxLayout(
            central
        )

        root_layout.setContentsMargins(
            15,
            15,
            15,
            15,
        )

        root_layout.setSpacing(
            10
        )

        # ====================================================
        # TITLE
        # ====================================================

        title = QLabel(
            "RIGEL UAV SIMULATOR"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setStyleSheet(
            """
            QLabel {
                font-size: 26px;
                font-weight: bold;
                padding: 10px;
            }
            """
        )

        root_layout.addWidget(
            title
        )

        # ====================================================
        # SCROLL
        # ====================================================

        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        content = QWidget()

        content_layout = QVBoxLayout(
            content
        )

        content_layout.setSpacing(
            10
        )

        scroll.setWidget(
            content
        )

        root_layout.addWidget(
            scroll
        )

        # ====================================================
        # STATUS
        # ====================================================

        self._create_status_panel(
            content_layout
        )

        # ====================================================
        # INITIAL CONFIG
        # ====================================================

        self.drone_config_panel = (
            DroneConfigPanel()
        )

        content_layout.addWidget(
            self.drone_config_panel
        )

        self.mavlink_config_panel = (
            MAVLinkConfigPanel()
        )

        content_layout.addWidget(
            self.mavlink_config_panel
        )

        # ====================================================
        # LIVE CONTROL
        # ====================================================

        self._create_live_control_panel(
            content_layout
        )

        # ====================================================
        # TELEMETRY
        # ====================================================

        self._create_telemetry_panel(
            content_layout
        )

        # ====================================================
        # STRETCH
        # ====================================================

        content_layout.addStretch()

    # ========================================================
    # STATUS PANEL
    # ========================================================

    def _create_status_panel(
        self,
        parent_layout,
    ):

        frame = QFrame()

        frame.setFrameShape(
            QFrame.StyledPanel
        )

        layout = QVBoxLayout(
            frame
        )

        # ====================================================
        # TITLE
        # ====================================================

        title = QLabel(
            "SIMULATION STATUS"
        )

        title.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: bold;
            }
            """
        )

        layout.addWidget(
            title
        )

        # ====================================================
        # STATUS
        # ====================================================

        self.status_label = QLabel(
            "Status: STOPPED"
        )

        self.status_label.setAlignment(
            Qt.AlignCenter
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
            }
            """
        )

        layout.addWidget(
            self.status_label
        )

        # ====================================================
        # MAVLINK
        # ====================================================

        self.mavlink_label = QLabel(
            "MAVLink: DISCONNECTED"
        )

        self.mavlink_label.setAlignment(
            Qt.AlignCenter
        )

        self.mavlink_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                padding: 5px;
            }
            """
        )

        layout.addWidget(
            self.mavlink_label
        )

        # ====================================================
        # START / STOP
        # ====================================================

        buttons = QHBoxLayout()

        self.start_button = QPushButton(
            "START"
        )

        self.stop_button = QPushButton(
            "STOP"
        )

        self.start_button.setMinimumHeight(
            40
        )

        self.stop_button.setMinimumHeight(
            40
        )

        self.stop_button.setEnabled(
            False
        )

        self.start_button.clicked.connect(
            self.start_simulation
        )

        self.stop_button.clicked.connect(
            self.stop_simulation
        )

        buttons.addWidget(
            self.start_button
        )

        buttons.addWidget(
            self.stop_button
        )

        layout.addLayout(
            buttons
        )

        parent_layout.addWidget(
            frame
        )

    # ========================================================
    # LIVE CONTROL
    # ========================================================

    def _create_live_control_panel(
        self,
        parent_layout,
    ):

        self.live_frame = QGroupBox(
            "LIVE SIMULATION CONTROL"
        )

        layout = QGridLayout(
            self.live_frame
        )

        layout.setHorizontalSpacing(
            10
        )

        layout.setVerticalSpacing(
            8
        )

        row = 0

        # ====================================================
        # MODE
        # ====================================================

        layout.addWidget(
            QLabel("Flight Mode"),
            row,
            0,
        )

        self.mode_combo = QComboBox()

        self.mode_combo.addItems([
            "FREE",
            "ALT_HOLD",
            "MISSION",
        ])

        self.mode_combo.currentTextChanged.connect(
            self.on_mode_changed
        )

        layout.addWidget(
            self.mode_combo,
            row,
            1,
            1,
            2,
        )

        row += 1

        # ====================================================
        # ALTITUDE
        # ====================================================

        layout.addWidget(
            QLabel("Altitude"),
            row,
            0,
        )

        self.altitude_spin = (
            QDoubleSpinBox()
        )

        self.altitude_spin.setRange(
            0.0,
            1000.0,
        )

        self.altitude_spin.setDecimals(
            2
        )

        self.altitude_spin.setSingleStep(
            1.0
        )

        self.altitude_spin.setSuffix(
            " m"
        )

        self.altitude_slider = QSlider(
            Qt.Horizontal
        )

        self.altitude_slider.setRange(
            0,
            100000,
        )

        self.altitude_slider.setSingleStep(
            100
        )

        self.altitude_button = QPushButton(
            "APPLY"
        )

        layout.addWidget(
            self.altitude_spin,
            row,
            1,
        )

        layout.addWidget(
            self.altitude_button,
            row,
            2,
        )

        row += 1

        layout.addWidget(
            self.altitude_slider,
            row,
            0,
            1,
            3,
        )

        self.altitude_button.clicked.connect(
            self.apply_altitude
        )

        self.altitude_slider.valueChanged.connect(
            self.on_altitude_slider_changed
        )

        self.altitude_spin.valueChanged.connect(
            self.on_altitude_spin_changed
        )

        row += 1

        # ====================================================
        # SPEED
        # ====================================================

        layout.addWidget(
            QLabel("Speed"),
            row,
            0,
        )

        self.speed_spin = (
            QDoubleSpinBox()
        )

        self.speed_spin.setRange(
            0.0,
            100.0,
        )

        self.speed_spin.setDecimals(
            2
        )

        self.speed_spin.setSingleStep(
            0.5
        )

        self.speed_spin.setSuffix(
            " m/s"
        )

        self.speed_slider = QSlider(
            Qt.Horizontal
        )

        self.speed_slider.setRange(
            0,
            10000,
        )

        self.speed_slider.setSingleStep(
            10
        )

        self.speed_button = QPushButton(
            "APPLY"
        )

        layout.addWidget(
            self.speed_spin,
            row,
            1,
        )

        layout.addWidget(
            self.speed_button,
            row,
            2,
        )

        row += 1

        layout.addWidget(
            self.speed_slider,
            row,
            0,
            1,
            3,
        )

        self.speed_button.clicked.connect(
            self.apply_speed
        )

        self.speed_slider.valueChanged.connect(
            self.on_speed_slider_changed
        )

        self.speed_spin.valueChanged.connect(
            self.on_speed_spin_changed
        )

        row += 1

        # ====================================================
        # HEADING
        # ====================================================

        layout.addWidget(
            QLabel("Heading"),
            row,
            0,
        )

        self.heading_spin = (
            QDoubleSpinBox()
        )

        self.heading_spin.setRange(
            0.0,
            360.0,
        )

        self.heading_spin.setDecimals(
            2
        )

        self.heading_spin.setSingleStep(
            1.0
        )

        self.heading_spin.setSuffix(
            " °"
        )

        self.heading_slider = QSlider(
            Qt.Horizontal
        )

        self.heading_slider.setRange(
            0,
            36000,
        )

        self.heading_slider.setSingleStep(
            100
        )

        self.heading_button = QPushButton(
            "APPLY"
        )

        layout.addWidget(
            self.heading_spin,
            row,
            1,
        )

        layout.addWidget(
            self.heading_button,
            row,
            2,
        )

        row += 1

        layout.addWidget(
            self.heading_slider,
            row,
            0,
            1,
            3,
        )

        self.heading_button.clicked.connect(
            self.apply_heading
        )

        self.heading_slider.valueChanged.connect(
            self.on_heading_slider_changed
        )

        self.heading_spin.valueChanged.connect(
            self.on_heading_spin_changed
        )

        row += 1

        # ====================================================
        # LATITUDE
        # ====================================================

        layout.addWidget(
            QLabel("Latitude"),
            row,
            0,
        )

        self.latitude_spin = (
            QDoubleSpinBox()
        )

        self.latitude_spin.setRange(
            -90.0,
            90.0,
        )

        self.latitude_spin.setDecimals(
            7
        )

        self.latitude_spin.setSingleStep(
            0.0001
        )

        self.latitude_button = QPushButton(
            "APPLY"
        )

        layout.addWidget(
            self.latitude_spin,
            row,
            1,
        )

        layout.addWidget(
            self.latitude_button,
            row,
            2,
        )

        self.latitude_button.clicked.connect(
            self.apply_latitude
        )

        row += 1

        # ====================================================
        # LONGITUDE
        # ====================================================

        layout.addWidget(
            QLabel("Longitude"),
            row,
            0,
        )

        self.longitude_spin = (
            QDoubleSpinBox()
        )

        self.longitude_spin.setRange(
            -180.0,
            180.0,
        )

        self.longitude_spin.setDecimals(
            7
        )

        self.longitude_spin.setSingleStep(
            0.0001
        )

        self.longitude_button = QPushButton(
            "APPLY"
        )

        layout.addWidget(
            self.longitude_spin,
            row,
            1,
        )

        layout.addWidget(
            self.longitude_button,
            row,
            2,
        )

        self.longitude_button.clicked.connect(
            self.apply_longitude
        )

        row += 1

        # ====================================================
        # ROLL
        # ====================================================

        layout.addWidget(
            QLabel("Roll"),
            row,
            0,
        )

        self.roll_spin = (
            QDoubleSpinBox()
        )

        self.roll_spin.setRange(
            -180.0,
            180.0,
        )

        self.roll_spin.setDecimals(
            2
        )

        self.roll_spin.setSuffix(
            " °"
        )

        self.roll_spin.valueChanged.connect(
            self.on_roll_changed
        )

        layout.addWidget(
            self.roll_spin,
            row,
            1,
            1,
            2,
        )

        row += 1

        # ====================================================
        # PITCH
        # ====================================================

        layout.addWidget(
            QLabel("Pitch"),
            row,
            0,
        )

        self.pitch_spin = (
            QDoubleSpinBox()
        )

        self.pitch_spin.setRange(
            -90.0,
            90.0,
        )

        self.pitch_spin.setDecimals(
            2
        )

        self.pitch_spin.setSuffix(
            " °"
        )

        self.pitch_spin.valueChanged.connect(
            self.on_pitch_changed
        )

        layout.addWidget(
            self.pitch_spin,
            row,
            1,
            1,
            2,
        )

        row += 1

        # ====================================================
        # YAW
        # ====================================================

        layout.addWidget(
            QLabel("Yaw"),
            row,
            0,
        )

        self.yaw_spin = (
            QDoubleSpinBox()
        )

        self.yaw_spin.setRange(
            0.0,
            360.0,
        )

        self.yaw_spin.setDecimals(
            2
        )

        self.yaw_spin.setSuffix(
            " °"
        )

        self.yaw_spin.valueChanged.connect(
            self.on_yaw_changed
        )

        layout.addWidget(
            self.yaw_spin,
            row,
            1,
            1,
            2,
        )

        row += 1

        # ====================================================
        # BATTERY
        # ====================================================

        layout.addWidget(
            QLabel("Battery"),
            row,
            0,
        )

        self.battery_spin = (
            QDoubleSpinBox()
        )

        self.battery_spin.setRange(
            0.0,
            100.0,
        )

        self.battery_spin.setDecimals(
            1
        )

        self.battery_spin.setSuffix(
            " %"
        )

        self.battery_button = QPushButton(
            "APPLY"
        )

        self.battery_button.clicked.connect(
            self.apply_battery
        )

        layout.addWidget(
            self.battery_spin,
            row,
            1,
        )

        layout.addWidget(
            self.battery_button,
            row,
            2,
        )

        row += 1

        # ====================================================
        # GPS FIX
        # ====================================================

        layout.addWidget(
            QLabel("GPS Fix"),
            row,
            0,
        )

        self.gps_fix_spin = QSpinBox()

        self.gps_fix_spin.setRange(
            0,
            6,
        )

        self.gps_fix_spin.setValue(
            3
        )

        layout.addWidget(
            self.gps_fix_spin,
            row,
            1,
        )

        row += 1

        # ====================================================
        # SATELLITES
        # ====================================================

        layout.addWidget(
            QLabel("Satellites"),
            row,
            0,
        )

        self.satellites_spin = QSpinBox()

        self.satellites_spin.setRange(
            0,
            255,
        )

        self.satellites_spin.setValue(
            12
        )

        layout.addWidget(
            self.satellites_spin,
            row,
            1,
        )

        self.gps_button = QPushButton(
            "APPLY GPS"
        )

        self.gps_button.clicked.connect(
            self.apply_gps
        )

        layout.addWidget(
            self.gps_button,
            row,
            2,
        )

        row += 1

        # ====================================================
        # HDOP
        # ====================================================

        layout.addWidget(
            QLabel("HDOP"),
            row,
            0,
        )

        self.hdop_spin = (
            QDoubleSpinBox()
        )

        self.hdop_spin.setRange(
            0.0,
            99.0,
        )

        self.hdop_spin.setDecimals(
            2
        )

        self.hdop_spin.setValue(
            1.0
        )

        layout.addWidget(
            self.hdop_spin,
            row,
            1,
        )

        row += 1

        # ====================================================
        # VDOP
        # ====================================================

        layout.addWidget(
            QLabel("VDOP"),
            row,
            0,
        )

        self.vdop_spin = (
            QDoubleSpinBox()
        )

        self.vdop_spin.setRange(
            0.0,
            99.0,
        )

        self.vdop_spin.setDecimals(
            2
        )

        self.vdop_spin.setValue(
            1.0
        )

        layout.addWidget(
            self.vdop_spin,
            row,
            1,
        )

        # ====================================================
        # ACTION BUTTONS
        # ====================================================

        row += 1

        action_layout = QHBoxLayout()

        self.arm_button = QPushButton(
            "ARM"
        )

        self.disarm_button = QPushButton(
            "DISARM"
        )

        self.takeoff_button = QPushButton(
            "TAKEOFF"
        )

        self.land_button = QPushButton(
            "LAND"
        )

        self.rtl_button = QPushButton(
            "RTL"
        )

        self.arm_button.clicked.connect(
            self.arm_drone
        )

        self.disarm_button.clicked.connect(
            self.disarm_drone
        )

        self.takeoff_button.clicked.connect(
            self.takeoff_drone
        )

        self.land_button.clicked.connect(
            self.land_drone
        )

        self.rtl_button.clicked.connect(
            self.rtl_drone
        )

        action_layout.addWidget(
            self.arm_button
        )

        action_layout.addWidget(
            self.disarm_button
        )

        action_layout.addWidget(
            self.takeoff_button
        )

        action_layout.addWidget(
            self.land_button
        )

        action_layout.addWidget(
            self.rtl_button
        )

        layout.addLayout(
            action_layout,
            row,
            0,
            1,
            3,
        )

        # ====================================================
        # INITIAL DISABLED STATE
        # ====================================================

        self.live_frame.setEnabled(
            False
        )

        parent_layout.addWidget(
            self.live_frame
        )

    # ========================================================
    # TELEMETRY PANEL
    # ========================================================

    def _create_telemetry_panel(
        self,
        parent_layout,
    ):

        frame = QGroupBox(
            "LIVE TELEMETRY"
        )

        layout = QGridLayout(
            frame
        )

        self.telemetry_mode = QLabel(
            "--"
        )

        self.telemetry_arm = QLabel(
            "--"
        )

        self.telemetry_lat = QLabel(
            "--"
        )

        self.telemetry_lon = QLabel(
            "--"
        )

        self.telemetry_alt = QLabel(
            "--"
        )

        self.telemetry_speed = QLabel(
            "--"
        )

        self.telemetry_heading = QLabel(
            "--"
        )

        self.telemetry_roll = QLabel(
            "--"
        )

        self.telemetry_pitch = QLabel(
            "--"
        )

        self.telemetry_yaw = QLabel(
            "--"
        )

        self.telemetry_battery = QLabel(
            "--"
        )

        self.telemetry_wp = QLabel(
            "--"
        )

        self.telemetry_distance = QLabel(
            "--"
        )

        self.telemetry_alt_error = QLabel(
            "--"
        )

        values = [

            ("Mode", self.telemetry_mode),
            ("Armed", self.telemetry_arm),

            ("Latitude", self.telemetry_lat),
            ("Longitude", self.telemetry_lon),

            ("Altitude", self.telemetry_alt),
            ("Speed", self.telemetry_speed),

            ("Heading", self.telemetry_heading),
            ("Roll", self.telemetry_roll),

            ("Pitch", self.telemetry_pitch),
            ("Yaw", self.telemetry_yaw),

            ("Battery", self.telemetry_battery),
            ("Current WP", self.telemetry_wp),

            ("Distance", self.telemetry_distance),
            ("Altitude Error", self.telemetry_alt_error),
        ]

        for index, (
            name,
            widget,
        ) in enumerate(values):

            r = index // 2

            c = (
                index % 2
            ) * 2

            layout.addWidget(
                QLabel(name),
                r,
                c,
            )

            layout.addWidget(
                widget,
                r,
                c + 1,
            )

        parent_layout.addWidget(
            frame
        )

    # ========================================================
    # START SIMULATION
    # ========================================================

    def start_simulation(
        self,
    ):

        # ----------------------------------------------------
        # Prevent duplicate worker
        # ----------------------------------------------------

        if self.worker is not None:

            if self.worker.isRunning():

                return

        # ----------------------------------------------------
        # Read initial configuration
        # ----------------------------------------------------

        try:

            drone_config = (
                self.drone_config_panel.get_config()
            )

        except Exception:

            drone_config = {
                "lat": 10.8231000,
                "lon": 106.6297000,
                "alt": 0.0,
            }

        try:

            mavlink_config = (
                self.mavlink_config_panel.get_config()
            )

        except Exception:

            mavlink_config = {
                "connection_string":
                    "udp:0.0.0.0:14550",

                "system_id":
                    1,

                "component_id":
                    1,
            }

        # ----------------------------------------------------
        # Create worker
        # ----------------------------------------------------

        self.worker = SimulationWorker(
            drone_config=drone_config,
            mavlink_config=mavlink_config,
            parent=self,
        )

        # ----------------------------------------------------
        # Signals
        # ----------------------------------------------------

        self.worker.telemetry_updated.connect(
            self.on_telemetry_updated
        )

        self.worker.status_changed.connect(
            self.on_status_changed
        )

        self.worker.error_occurred.connect(
            self.on_error
        )

        self.worker.finished.connect(
            self.on_worker_finished
        )

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.status_label.setText(
            "Status: STARTING..."
        )

        self.mavlink_label.setText(
            "MAVLink: CONNECTING..."
        )

        self.start_button.setEnabled(
            False
        )

        self.stop_button.setEnabled(
            True
        )

        self.live_frame.setEnabled(
            False
        )

        # ----------------------------------------------------
        # Start
        # ----------------------------------------------------

        self.worker.start()

    # ========================================================
    # STOP SIMULATION
    # ========================================================

    def stop_simulation(
        self,
    ):

        if self.worker is None:

            return

        self.status_label.setText(
            "Status: STOPPING..."
        )

        self.stop_button.setEnabled(
            False
        )

        self.worker.stop()

    # ========================================================
    # WORKER FINISHED
    # ========================================================

    def on_worker_finished(
        self,
    ):

        worker = self.worker

        self.worker = None

        self.live_frame.setEnabled(
            False
        )

        self.start_button.setEnabled(
            True
        )

        self.stop_button.setEnabled(
            False
        )

        self.status_label.setText(
            "Status: STOPPED"
        )

        self.mavlink_label.setText(
            "MAVLink: DISCONNECTED"
        )

        if worker is not None:

            worker.deleteLater()

    # ========================================================
    # STATUS
    # ========================================================

    def on_status_changed(
        self,
        status,
    ):

        status = str(
            status
        ).upper()

        if status in (
            "RUNNING",
            "READY",
        ):

            self.status_label.setText(
                "Status: RUNNING"
            )

            self.mavlink_label.setText(
                "MAVLink: CONNECTED"
            )

            self.live_frame.setEnabled(
                True
            )

        elif status == "STOPPED":

            self.status_label.setText(
                "Status: STOPPED"
            )

            self.mavlink_label.setText(
                "MAVLink: DISCONNECTED"
            )

            self.live_frame.setEnabled(
                False
            )

        elif status == "ERROR":

            self.status_label.setText(
                "Status: ERROR"
            )

            self.live_frame.setEnabled(
                False
            )

    # ========================================================
    # TELEMETRY
    # ========================================================

    def on_telemetry_updated(
        self,
        status,
    ):

        if not isinstance(
            status,
            dict,
        ):

            return

        # ====================================================
        # VALUES
        # ====================================================

        mode = status.get(
            "flight_mode",
            status.get(
                "mode",
                "FREE",
            ),
        )

        armed = status.get(
            "armed",
            False,
        )

        lat = status.get(
            "lat",
            0.0,
        )

        lon = status.get(
            "lon",
            0.0,
        )

        alt = status.get(
            "alt",
            0.0,
        )

        speed = status.get(
            "ground_speed",
            0.0,
        )

        heading = status.get(
            "heading",
            0.0,
        )

        roll = status.get(
            "roll",
            0.0,
        )

        pitch = status.get(
            "pitch",
            0.0,
        )

        yaw = status.get(
            "yaw",
            0.0,
        )

        battery = status.get(
            "battery",
            0.0,
        )

        current_wp = status.get(
            "current_waypoint",
            None,
        )

        mission_count = int(
            status.get(
                "mission_count",
                0,
            )
        )

        distance = status.get(
            "distance_to_target",
            None,
        )

        altitude_error = status.get(
            "altitude_error",
            None,
        )

        # ====================================================
        # DISPLAY
        # ====================================================

        self.telemetry_mode.setText(
            str(mode)
        )

        self.telemetry_arm.setText(
            str(armed)
        )

        self.telemetry_lat.setText(
            self._format_float(
                lat,
                7,
            )
        )

        self.telemetry_lon.setText(
            self._format_float(
                lon,
                7,
            )
        )

        self.telemetry_alt.setText(
            f"{self._to_float(alt):.2f} m"
        )

        self.telemetry_speed.setText(
            f"{self._to_float(speed):.2f} m/s"
        )

        self.telemetry_heading.setText(
            f"{self._to_float(heading):.2f}°"
        )

        self.telemetry_roll.setText(
            f"{self._to_float(roll):.2f}°"
        )

        self.telemetry_pitch.setText(
            f"{self._to_float(pitch):.2f}°"
        )

        self.telemetry_yaw.setText(
            f"{self._to_float(yaw):.2f}°"
        )

        self.telemetry_battery.setText(
            f"{self._to_float(battery):.1f} %"
        )

        # ====================================================
        # WP
        # ====================================================

        if (
            current_wp is not None
            and mission_count > 0
        ):

            self.telemetry_wp.setText(
                f"{current_wp} / "
                f"{mission_count}"
            )

        else:

            self.telemetry_wp.setText(
                "--"
            )

        # ====================================================
        # DISTANCE
        # ====================================================

        if distance is None:

            self.telemetry_distance.setText(
                "--"
            )

        else:

            self.telemetry_distance.setText(
                f"{self._to_float(distance):.2f} m"
            )

        # ====================================================
        # ALT ERROR
        # ====================================================

        if altitude_error is None:

            self.telemetry_alt_error.setText(
                "--"
            )

        else:

            self.telemetry_alt_error.setText(
                f"{self._to_float(altitude_error):.2f} m"
            )

        # ====================================================
        # SYNC CONTROLS
        # ====================================================

        self._sync_double_spin(
            self.altitude_spin,
            status.get(
                "target_altitude",
                None,
            ),
        )

        self._sync_double_spin(
            self.speed_spin,
            status.get(
                "target_ground_speed",
                None,
            ),
        )

        self._sync_double_spin(
            self.heading_spin,
            status.get(
                "target_heading",
                None,
            ),
        )

        self._sync_double_spin(
            self.latitude_spin,
            lat,
        )

        self._sync_double_spin(
            self.longitude_spin,
            lon,
        )

        self._sync_double_spin(
            self.roll_spin,
            roll,
        )

        self._sync_double_spin(
            self.pitch_spin,
            pitch,
        )

        self._sync_double_spin(
            self.yaw_spin,
            yaw,
        )

        self._sync_double_spin(
            self.battery_spin,
            battery,
        )

        self._sync_double_spin(
            self.hdop_spin,
            status.get(
                "gps_hdop",
                None,
            ),
        )

        self._sync_double_spin(
            self.vdop_spin,
            status.get(
                "gps_vdop",
                None,
            ),
        )

        self._sync_int_spin(
            self.gps_fix_spin,
            status.get(
                "gps_fix",
                None,
            ),
        )

        self._sync_int_spin(
            self.satellites_spin,
            status.get(
                "satellites",
                None,
            ),
        )

        # ====================================================
        # SLIDERS
        # ====================================================

        self._sync_slider(
            self.altitude_slider,
            status.get(
                "target_altitude",
                None,
            ),
            100.0,
        )

        self._sync_slider(
            self.speed_slider,
            status.get(
                "target_ground_speed",
                None,
            ),
            100.0,
        )

        self._sync_slider(
            self.heading_slider,
            status.get(
                "target_heading",
                None,
            ),
            100.0,
        )

        # ====================================================
        # MODE COMBO
        # ====================================================

        mode_text = str(
            mode
        ).upper()

        index = (
            self.mode_combo.findText(
                mode_text
            )
        )

        if index >= 0:

            old_block = (
                self.mode_combo.blockSignals(
                    True
                )
            )

            self.mode_combo.setCurrentIndex(
                index
            )

            self.mode_combo.blockSignals(
                old_block
            )

    # ========================================================
    # MODE
    # ========================================================

    def on_mode_changed(
        self,
        mode,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "mode",
            mode,
        )

    # ========================================================
    # ALTITUDE SLIDER
    # ========================================================

    def on_altitude_slider_changed(
        self,
        value,
    ):

        altitude = (
            float(value)
            / 100.0
        )

        self._set_double_without_signal(
            self.altitude_spin,
            altitude,
        )

        if self._worker_running():

            self.worker.queue_command(
                "altitude",
                altitude,
            )

    # ========================================================

    def on_altitude_spin_changed(
        self,
        value,
    ):

        slider_value = int(
            value * 100.0
        )

        self._set_slider_without_signal(
            self.altitude_slider,
            slider_value,
        )

    # ========================================================
    # SPEED SLIDER
    # ========================================================

    def on_speed_slider_changed(
        self,
        value,
    ):

        speed = (
            float(value)
            / 100.0
        )

        self._set_double_without_signal(
            self.speed_spin,
            speed,
        )

        if self._worker_running():

            self.worker.queue_command(
                "speed",
                speed,
            )

    # ========================================================

    def on_speed_spin_changed(
        self,
        value,
    ):

        slider_value = int(
            value * 100.0
        )

        self._set_slider_without_signal(
            self.speed_slider,
            slider_value,
        )

    # ========================================================
    # HEADING SLIDER
    # ========================================================

    def on_heading_slider_changed(
        self,
        value,
    ):

        heading = (
            float(value)
            / 100.0
        )

        self._set_double_without_signal(
            self.heading_spin,
            heading,
        )

        if self._worker_running():

            self.worker.queue_command(
                "heading",
                heading,
            )

    # ========================================================

    def on_heading_spin_changed(
        self,
        value,
    ):

        slider_value = int(
            value * 100.0
        )

        self._set_slider_without_signal(
            self.heading_slider,
            slider_value,
        )

    # ========================================================
    # APPLY ALTITUDE
    # ========================================================

    def apply_altitude(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "altitude",
            self.altitude_spin.value(),
        )

    # ========================================================
    # APPLY SPEED
    # ========================================================

    def apply_speed(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "speed",
            self.speed_spin.value(),
        )

    # ========================================================
    # APPLY HEADING
    # ========================================================

    def apply_heading(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "heading",
            self.heading_spin.value(),
        )

    # ========================================================
    # LATITUDE
    # ========================================================

    def apply_latitude(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "latitude",
            self.latitude_spin.value(),
        )

    # ========================================================
    # LONGITUDE
    # ========================================================

    def apply_longitude(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "longitude",
            self.longitude_spin.value(),
        )

    # ========================================================
    # ROLL
    # ========================================================

    def on_roll_changed(
        self,
        value,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "roll",
            value,
        )

    # ========================================================
    # PITCH
    # ========================================================

    def on_pitch_changed(
        self,
        value,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "pitch",
            value,
        )

    # ========================================================
    # YAW
    # ========================================================

    def on_yaw_changed(
        self,
        value,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "yaw",
            value,
        )

    # ========================================================
    # BATTERY
    # ========================================================

    def apply_battery(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "battery",
            self.battery_spin.value(),
        )

    # ========================================================
    # GPS
    # ========================================================

    def apply_gps(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "gps",
            {
                "fix_type":
                    self.gps_fix_spin.value(),

                "satellites":
                    self.satellites_spin.value(),

                "hdop":
                    self.hdop_spin.value(),

                "vdop":
                    self.vdop_spin.value(),
            },
        )

    # ========================================================
    # ARM
    # ========================================================

    def arm_drone(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "arm"
        )

    # ========================================================
    # DISARM
    # ========================================================

    def disarm_drone(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "disarm"
        )

    # ========================================================
    # TAKEOFF
    # ========================================================

    def takeoff_drone(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "takeoff",
            self.altitude_spin.value(),
        )

    # ========================================================
    # LAND
    # ========================================================

    def land_drone(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "land"
        )

    # ========================================================
    # RTL
    # ========================================================

    def rtl_drone(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "rtl"
        )

    # ========================================================
    # WORKER CHECK
    # ========================================================

    def _worker_running(
        self,
    ) -> bool:

        return (
            self.worker is not None
            and
            self.worker.isRunning()
        )

    # ========================================================
    # SYNC DOUBLE
    # ========================================================

    @staticmethod
    def _sync_double_spin(
        widget,
        value,
    ):

        if value is None:

            return

        try:

            value = float(
                value
            )

            old_block = (
                widget.blockSignals(
                    True
                )
            )

            widget.setValue(
                value
            )

            widget.blockSignals(
                old_block
            )

        except (
            TypeError,
            ValueError,
        ):

            pass

    # ========================================================
    # SYNC INT
    # ========================================================

    @staticmethod
    def _sync_int_spin(
        widget,
        value,
    ):

        if value is None:

            return

        try:

            value = int(
                value
            )

            old_block = (
                widget.blockSignals(
                    True
                )
            )

            widget.setValue(
                value
            )

            widget.blockSignals(
                old_block
            )

        except (
            TypeError,
            ValueError,
        ):

            pass

    # ========================================================
    # SYNC SLIDER
    # ========================================================

    @staticmethod
    def _sync_slider(
        widget,
        value,
        scale=1.0,
    ):

        if value is None:

            return

        try:

            slider_value = int(
                float(value)
                * scale
            )

            old_block = widget.blockSignals(
                True
            )

            widget.setValue(
                slider_value
            )

            widget.blockSignals(
                old_block
            )

        except (
            TypeError,
            ValueError,
        ):

            pass

    # ========================================================
    # SET DOUBLE WITHOUT SIGNAL
    # ========================================================

    @staticmethod
    def _set_double_without_signal(
        widget,
        value,
    ):

        old_block = (
            widget.blockSignals(
                True
            )
        )

        widget.setValue(
            value
        )

        widget.blockSignals(
            old_block
        )

    # ========================================================
    # SET SLIDER WITHOUT SIGNAL
    # ========================================================

    @staticmethod
    def _set_slider_without_signal(
        widget,
        value,
    ):

        old_block = (
            widget.blockSignals(
                True
            )
        )

        widget.setValue(
            value
        )

        widget.blockSignals(
            old_block
        )

    # ========================================================
    # FORMAT FLOAT
    # ========================================================

    @staticmethod
    def _format_float(
        value,
        decimals,
    ):

        try:

            return (
                f"{float(value):.{decimals}f}"
            )

        except (
            TypeError,
            ValueError,
        ):

            return "--"

    # ========================================================
    # TO FLOAT
    # ========================================================

    @staticmethod
    def _to_float(
        value,
        default=0.0,
    ):

        try:

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    # ========================================================
    # ERROR
    # ========================================================

    def on_error(
        self,
        message,
    ):

        self.status_label.setText(
            "Status: ERROR"
        )

        self.mavlink_label.setText(
            f"MAVLink ERROR: {message}"
        )

        self.live_frame.setEnabled(
            False
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event,
    ):

        if self.worker is not None:

            self.worker.stop()

            if self.worker.isRunning():

                self.worker.wait()

            self.worker = None

        event.accept()