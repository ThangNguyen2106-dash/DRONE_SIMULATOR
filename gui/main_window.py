from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import (
    QApplication,
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
    QAbstractSpinBox,
    QMessageBox,
)

from gui.simulation_worker import SimulationWorker
from gui.drone_config_panel import DroneConfigPanel
from gui.mavlink_config_panel import MAVLinkConfigPanel
from gui.joystick_panel import JoystickPanel
from gui.mission_panel import MissionPanel


# ============================================================
# GLOBAL MOUSE WHEEL FILTER
# ============================================================

class NoSpinBoxWheelFilter(QObject):
    """
    Disable mouse wheel changes for every QSpinBox /
    QDoubleSpinBox in the entire application.

    This also handles the internal QLineEdit and child
    widgets belonging to a SpinBox.
    """

    def eventFilter(
        self,
        watched,
        event,
    ):

        # ----------------------------------------------------
        # Only process Wheel events.
        # ----------------------------------------------------

        if event.type() != QEvent.Type.Wheel:

            return False

        # ----------------------------------------------------
        # Start from the widget receiving the event.
        # ----------------------------------------------------

        current = watched

        # ----------------------------------------------------
        # Walk through the parent hierarchy.
        #
        # Example:
        #
        # QLineEdit
        #    ↓
        # QDoubleSpinBox
        #    ↓
        # QWidget
        #
        # If any parent is a SpinBox, block the wheel.
        # ----------------------------------------------------

        while current is not None:

            if isinstance(
                current,
                QAbstractSpinBox,
            ):

                event.accept()

                return True

            try:

                current = current.parent()

            except Exception:

                break

        return False


# ============================================================
# CUSTOM DOUBLE SPINBOX
# ============================================================

class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """
    Local protection for QDoubleSpinBox.
    """

    def wheelEvent(
        self,
        event,
    ):

        event.accept()

        return


# ============================================================
# CUSTOM SPINBOX
# ============================================================

class NoWheelSpinBox(QSpinBox):
    """
    Local protection for QSpinBox.
    """

    def wheelEvent(
        self,
        event,
    ):

        event.accept()

        return


# ============================================================
# MAIN WINDOW
# ============================================================

class MainWindow(QMainWindow):

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        parent=None,
    ):

        super().__init__(
            parent
        )

        # ====================================================
        # WINDOW
        # ====================================================

        self.setWindowTitle(
            "RIGEL UAV Simulator"
        )

        self.setMinimumSize(
            900,
            620,
        )

        # ====================================================
        # WORKER
        # ====================================================

        self.worker = None

        self._drone_armed = False

        self._drone_alt = 0.0

        self._joystick_warned = False

        # ====================================================
        # GLOBAL WHEEL FILTER
        # ====================================================

        self._wheel_filter = None

        app = QApplication.instance()

        if app is not None:

            self._wheel_filter = (
                NoSpinBoxWheelFilter(
                    app
                )
            )

            app.installEventFilter(
                self._wheel_filter
            )

        # ====================================================
        # UI
        # ====================================================

        self._setup_ui()

    # ========================================================
    # SETUP UI
    # ========================================================

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        title = QLabel("RIGEL UAV SIMULATOR")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root_layout.addWidget(title)

        self._create_status_panel(root_layout)

        # Responsive two-column workspace:
        # left = always-visible 3D flight view + key telemetry
        # right = scrollable configuration/control/mission panels.
        from PySide6.QtWidgets import QSplitter
        from gui.drone_3d_widget import Drone3DWidget

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        view_frame = QGroupBox("3D FLIGHT VIEW")
        view_layout = QVBoxLayout(view_frame)
        view_layout.setContentsMargins(4, 4, 4, 4)
        self.drone_3d = Drone3DWidget()
        view_layout.addWidget(self.drone_3d)
        left_layout.addWidget(view_frame, 1)

        quick = QFrame()
        quick.setObjectName("quickTelemetry")
        qgrid = QGridLayout(quick)
        qgrid.setContentsMargins(12, 8, 12, 8)
        self.quick_alt = QLabel("0.00 m")
        self.quick_speed = QLabel("0.00 m/s")
        self.quick_mode = QLabel("STANDBY")
        self.quick_battery = QLabel("100 %")
        self.quick_wp = QLabel("--")
        quick_items = [
            ("ALT", self.quick_alt), ("SPEED", self.quick_speed),
            ("MODE", self.quick_mode), ("BATTERY", self.quick_battery),
            ("WP", self.quick_wp),
        ]
        for i, (name, value) in enumerate(quick_items):
            qgrid.addWidget(QLabel(name), 0, i)
            qgrid.addWidget(value, 1, i)
        left_layout.addWidget(quick)

        splitter.addWidget(left)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setMaximumWidth(980)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(8)

        self.drone_config_panel = DroneConfigPanel()
        content_layout.addWidget(self.drone_config_panel)

        self.mavlink_config_panel = MAVLinkConfigPanel()
        self.mavlink_config_panel.on_debug_toggled = self._on_telemetry_debug_toggled
        content_layout.addWidget(self.mavlink_config_panel)

        self._create_live_control_panel(content_layout)

        self.joystick_panel = JoystickPanel()
        self.joystick_panel.on_command = self._on_joystick_command
        content_layout.addWidget(self.joystick_panel)

        self.mission_panel = MissionPanel()
        self.mission_panel.on_command = self._on_mission_command
        content_layout.addWidget(self.mission_panel)

        self._create_telemetry_panel(content_layout)
        content_layout.addStretch()

        scroll.setWidget(content)
        splitter.addWidget(scroll)

        root_layout.addWidget(splitter, 1)

        self._apply_modern_style()

    def _apply_modern_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #0b1220;
                color: #dce6f2;
                font-family: "Segoe UI";
                font-size: 10pt;
            }
            #appTitle {
                font-size: 20pt;
                font-weight: 700;
                padding: 2px 4px 4px 4px;
                color: #f1f6fb;
            }
            QFrame, QGroupBox {
                background: #111b2b;
                border: 1px solid #24354a;
                border-radius: 10px;
            }
            QGroupBox {
                margin-top: 9px;
                padding-top: 12px;
                font-weight: 700;
                color: #a9bfd5;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
                background: #111b2b;
            }
            QPushButton {
                background: #1c3047;
                border: 1px solid #31506f;
                border-radius: 7px;
                padding: 7px 12px;
                min-height: 28px;
            }
            QPushButton:hover { background: #284461; }
            QPushButton:pressed { background: #14283d; }
            QPushButton:disabled { color: #627386; background: #131d29; }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background: #0c1625;
                border: 1px solid #2b425c;
                border-radius: 6px;
                padding: 5px 7px;
                min-height: 26px;
            }
            QSlider::groove:horizontal {
                height: 5px; background: #26384d; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px; margin: -5px 0; border-radius: 7px;
                background: #5d9bd3;
            }
            QTableWidget {
                background: #0c1625;
                alternate-background-color: #101d2e;
                gridline-color: #25384d;
                border: 1px solid #24354a;
            }
            QHeaderView::section {
                background: #17263a;
                color: #b9cce0;
                padding: 6px;
                border: 0;
            }
            #quickTelemetry QLabel {
                background: transparent;
                border: 0;
            }
        """)

    # ========================================================
    # STATUS PANEL
    # ========================================================

    def _create_status_panel(
        self,
        parent_layout,
    ):

        # Single-row "web header" style bar: status text, the
        # MAVLink LED + label, and START/STOP all inline, kept
        # in root_layout (outside the scroll area) so it stays
        # pinned at the top of the window at all times.

        frame = QFrame()

        frame.setFrameShape(
            QFrame.StyledPanel
        )

        layout = QHBoxLayout(
            frame
        )

        self.status_label = QLabel(
            "Status: STOPPED"
        )

        self.status_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 5px;
            }
            """
        )

        layout.addWidget(
            self.status_label
        )

        layout.addStretch()

        # LED-style connection indicator: red = disconnected,
        # yellow = connecting, green = connected. Just a small
        # round QLabel colored via stylesheet, no image assets
        # needed.

        self.mavlink_led = QLabel()

        self.mavlink_led.setFixedSize(14, 14)

        self._set_mavlink_led(False)

        layout.addWidget(
            self.mavlink_led
        )

        self.mavlink_label = QLabel(
            "MAVLink: DISCONNECTED"
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

        layout.addStretch()

        # LED-style arm indicator: red = disarmed, green = armed.

        self.arm_led = QLabel()

        self.arm_led.setFixedSize(14, 14)

        layout.addWidget(
            self.arm_led
        )

        self.arm_label = QLabel(
            "DISARMED"
        )

        self.arm_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }
            """
        )

        layout.addWidget(
            self.arm_label
        )

        self._set_arm_led(False)

        layout.addStretch()

        # ====================================================
        # START / STOP
        # ====================================================

        self.start_button = QPushButton(
            "START"
        )

        self.stop_button = QPushButton(
            "STOP"
        )

        self.start_button.setMinimumHeight(
            36
        )

        self.stop_button.setMinimumHeight(
            36
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

        layout.addWidget(
            self.start_button
        )

        layout.addWidget(
            self.stop_button
        )

        parent_layout.addWidget(
            frame
        )

    # ========================================================
    # LIVE CONTROL PANEL
    # ========================================================

    def _create_live_control_panel(
        self,
        parent_layout,
    ):
        """
        Compact flight-control panel.

        Continuous flight control belongs to the virtual
        joystick, so the old altitude/speed/heading sliders,
        attitude editors and GPS adjustment controls are not
        duplicated here anymore. This panel is intentionally
        limited to mode and discrete flight actions.
        """

        self.live_frame = QGroupBox(
            "FLIGHT CONTROL"
        )

        layout = QGridLayout(
            self.live_frame
        )
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)

        layout.addWidget(
            QLabel("Mode"),
            0,
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
            0,
            1,
            1,
            3,
        )

        self.arm_button = QPushButton("ARM")
        self.disarm_button = QPushButton("DISARM")
        self.takeoff_button = QPushButton("TAKEOFF")
        self.land_button = QPushButton("LAND")
        self.rtl_button = QPushButton("RETURN TO HOME")
        self.set_home_button = QPushButton("SET HOME HERE")

        self.arm_button.clicked.connect(self.arm_drone)
        self.disarm_button.clicked.connect(self.disarm_drone)
        self.takeoff_button.clicked.connect(self.takeoff_drone)
        self.land_button.clicked.connect(self.land_drone)
        self.rtl_button.clicked.connect(self.rtl_drone)
        self.set_home_button.clicked.connect(self.set_home_here)

        buttons = [
            self.arm_button,
            self.disarm_button,
            self.takeoff_button,
            self.land_button,
            self.rtl_button,
            self.set_home_button,
        ]

        for i, button in enumerate(buttons):
            layout.addWidget(
                button,
                1 + i // 3,
                i % 3,
            )

        hint = QLabel(
            "Joystick: LEFT = yaw / climb · RIGHT = move / tilt"
        )
        hint.setObjectName("controlHint")
        layout.addWidget(
            hint,
            3,
            0,
            1,
            3,
        )

        self.live_frame.setEnabled(False)
        parent_layout.addWidget(self.live_frame)

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

        self.telemetry_mode = QLabel("--")
        self.telemetry_arm = QLabel("--")
        self.telemetry_lat = QLabel("--")
        self.telemetry_lon = QLabel("--")
        self.telemetry_alt = QLabel("--")
        self.telemetry_speed = QLabel("--")
        self.telemetry_heading = QLabel("--")
        self.telemetry_roll = QLabel("--")
        self.telemetry_pitch = QLabel("--")
        self.telemetry_yaw = QLabel("--")
        self.telemetry_battery = QLabel("--")
        self.telemetry_wp = QLabel("--")
        self.telemetry_distance = QLabel("--")
        self.telemetry_alt_error = QLabel("--")

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

            row = index // 2

            column = (
                index % 2
            ) * 2

            layout.addWidget(
                QLabel(name),
                row,
                column,
            )

            layout.addWidget(
                widget,
                row,
                column + 1,
            )

        parent_layout.addWidget(
            frame
        )

    # ========================================================
    # START
    # ========================================================

    def start_simulation(
        self,
    ):

        if self.worker is not None:

            if self.worker.isRunning():

                return

        # ----------------------------------------------------
        # Drone configuration
        # ----------------------------------------------------

        try:

            drone_config = (
                self.drone_config_panel.get_config()
            )

        except Exception as exc:

            print(
                "[GUI] Drone config error:",
                exc,
            )

            drone_config = {
                "lat": 10.8231000,
                "lon": 106.6297000,
                "alt": 0.0,
            }

        # ----------------------------------------------------
        # MAVLink configuration
        # ----------------------------------------------------

        try:

            mavlink_config = (
                self.mavlink_config_panel.get_config()
            )

        except Exception as exc:

            print(
                "[GUI] MAVLink config error:",
                exc,
            )

            mavlink_config = {
                "connection_string":
                    "udp:0.0.0.0:14550",
                "system_id": 1,
                "component_id": 1,
            }

        # ====================================================
        # CREATE WORKER
        # ====================================================

        self.worker = SimulationWorker(
            drone_config=drone_config,
            mavlink_config=mavlink_config,
            parent=self,
        )

        # ====================================================
        # SIGNALS
        # ====================================================

        self.worker.telemetry_updated.connect(
            self.on_telemetry_updated
        )

        self.worker.status_changed.connect(
            self.on_status_changed
        )

        self.worker.mission_updated.connect(
            self.mission_panel.set_waypoints
        )

        self.worker.error_occurred.connect(
            self.on_error
        )

        self.worker.finished.connect(
            self.on_worker_finished
        )

        # ====================================================
        # UI
        # ====================================================

        self.status_label.setText(
            "Status: STARTING..."
        )

        self.mavlink_label.setText(
            "MAVLink: CONNECTING..."
        )

        self._set_mavlink_led(
            False,
            connecting=True,
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

        # Home (RTL target) is only read from this panel once,
        # at Drone creation below — editing it after START has
        # no effect on the running drone, which is confusing.
        # Lock it until STOP.

        self.drone_config_panel.set_enabled(
            False
        )

        # ====================================================
        # START
        # ====================================================

        self.worker.start()

    # ========================================================
    # STOP
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

        self.joystick_panel.set_enabled(
            False
        )

        self.mission_panel.set_enabled(
            False
        )

        self.drone_config_panel.set_enabled(
            True
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

        self._set_mavlink_led(False)

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

            self._set_mavlink_led(True)

            self.live_frame.setEnabled(
                True
            )

            self.joystick_panel.set_enabled(
                True
            )

            self.mission_panel.set_enabled(
                True
            )

        elif status == "STOPPED":

            self._drone_armed = False

            self._joystick_warned = False

            self._set_arm_led(False)

            self.status_label.setText(
                "Status: STOPPED"
            )

            self.mavlink_label.setText(
                "MAVLink: DISCONNECTED"
            )

            self._set_mavlink_led(False)

            self.live_frame.setEnabled(
                False
            )

            self.joystick_panel.set_enabled(
                False
            )

            self.mission_panel.set_enabled(
                False
            )

        elif status == "ERROR":

            self.status_label.setText(
                "Status: ERROR"
            )

            self.mavlink_label.setText(
                "MAVLink: ERROR"
            )

            self._set_mavlink_led(False)

            self.live_frame.setEnabled(
                False
            )

            self.joystick_panel.set_enabled(
                False
            )

            self.mission_panel.set_enabled(
                False
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

        self._set_double_silent(
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

        self._set_slider_silent(
            self.altitude_slider,
            int(
                value * 100.0
            ),
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

        self._set_double_silent(
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

        self._set_slider_silent(
            self.speed_slider,
            int(
                value * 100.0
            ),
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

        self._set_double_silent(
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

        self._set_slider_silent(
            self.heading_slider,
            int(
                value * 100.0
            ),
        )

    # ========================================================
    # APPLY ALTITUDE
    # ========================================================

    def apply_altitude(
        self,
    ):

        if not self._worker_running():

            return

        if not self._require_armed():

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

        if not self._require_armed():

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

        if not self._require_armed():

            return

        self.worker.queue_command(
            "heading",
            self.heading_spin.value(),
        )

    # ========================================================
    # APPLY LATITUDE
    # ========================================================

    def apply_latitude(
        self,
    ):

        if not self._worker_running():

            return

        if not self._require_armed():

            return

        self.worker.queue_command(
            "latitude",
            self.latitude_spin.value(),
        )

    # ========================================================
    # APPLY LONGITUDE
    # ========================================================

    def apply_longitude(
        self,
    ):

        if not self._worker_running():

            return

        if not self._require_armed():

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

        self.status_label.setText(
            "Status: ARMING..."
        )

    # ========================================================
    # DISARM
    # ========================================================

    def disarm_drone(
        self,
    ):

        if not self._worker_running():

            return

        if self._drone_alt > 0.05:

            QMessageBox.warning(
                self,
                "Không thể DISARM",
                "Drone đang bay có độ cao "
                f"({self._drone_alt:.1f} m).\n"
                "Vui lòng hạ cánh (LAND/RTL) trước khi DISARM.",
            )

            return

        self.worker.queue_command(
            "disarm"
        )

        self.status_label.setText(
            "Status: DISARMING..."
        )

    # ========================================================
    # REQUIRE ARMED
    # ========================================================

    def _require_armed(
        self,
    ) -> bool:

        if self._drone_armed:

            return True

        QMessageBox.warning(
            self,
            "Chưa ARM",
            "Drone chưa được ARM.\n"
            "Vui lòng bấm ARM trước khi thực hiện thao tác bay.",
        )

        return False

    # ========================================================
    # TAKEOFF
    # ========================================================

    def takeoff_drone(
        self,
    ):

        if not self._worker_running():

            return

        if not self._require_armed():

            return

        # Altitude is controlled by the joystick/flight logic now.
        # Use the simulator's standard takeoff target instead of a removed slider.
        self.worker.queue_command(
            "takeoff",
            10.0,
        )

        self.status_label.setText(
            "Status: TAKEOFF..."
        )

    # ========================================================
    # LAND
    # ========================================================

    def land_drone(
        self,
    ):

        if not self._worker_running():

            return

        if not self._require_armed():

            return

        self.worker.queue_command(
            "land"
        )

        self.status_label.setText(
            "Status: LANDING..."
        )

    # ========================================================
    # RTL
    # ========================================================

    def rtl_drone(
        self,
    ):

        if not self._worker_running():

            return

        if not self._require_armed():

            return

        self.worker.queue_command(
            "rtl"
        )

        self.status_label.setText(
            "Status: RETURN TO HOME..."
        )

    def set_home_here(
        self,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "set_home"
        )

        self.status_label.setText(
            "Status: HOME POSITION SET"
        )

    # ========================================================
    # JOYSTICK
    # ========================================================

    def _on_joystick_command(
        self,
        command,
        value,
    ):

        if not self._worker_running():

            return

        if not self._drone_armed:

            if not self._joystick_warned:

                self._joystick_warned = True

                self._require_armed()

            return

        self.worker.queue_command(
            command,
            value,
        )

    # ========================================================
    # MAVLINK LED
    # ========================================================

    def _set_mavlink_led(
        self,
        connected,
        connecting=False,
    ):

        if connecting:

            color = "#e6b800"

        elif connected:

            color = "#2ecc71"

        else:

            color = "#e74c3c"

        self.mavlink_led.setStyleSheet(
            f"""
            QLabel {{
                background-color: {color};
                border-radius: 7px;
                border: 1px solid #00000033;
            }}
            """
        )

    # ========================================================
    # ARM LED
    # ========================================================

    def _set_arm_led(
        self,
        armed,
    ):

        if armed:

            color = "#2ecc71"

            text = "ARMED"

        else:

            color = "#e74c3c"

            text = "DISARMED"

        self.arm_led.setStyleSheet(
            f"""
            QLabel {{
                background-color: {color};
                border-radius: 7px;
                border: 1px solid #00000033;
            }}
            """
        )

        self.arm_label.setText(
            text
        )

    # ========================================================
    # TELEMETRY DEBUG
    # ========================================================

    def _on_telemetry_debug_toggled(
        self,
        enabled,
    ):

        if not self._worker_running():

            return

        self.worker.queue_command(
            "telemetry_debug",
            bool(enabled),
        )

    # ========================================================
    # MISSION
    # ========================================================

    def _on_mission_command(
        self,
        command,
        value,
    ):

        if not self._worker_running():

            return

        if (
            command == "start_mission"
            and not self._require_armed()
        ):

            return

        self.worker.queue_command(
            command,
            value,
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

        # ----------------------------------------------------
        # 3D view + compact dashboard
        # ----------------------------------------------------
        if hasattr(self, "drone_3d"):
            self.drone_3d.update_telemetry(status)
        if hasattr(self, "quick_alt"):
            self.quick_alt.setText(f"{self._to_float(alt):.2f} m")
            self.quick_speed.setText(f"{self._to_float(speed):.2f} m/s")
            self.quick_mode.setText(str(mode).upper())
            self.quick_battery.setText(f"{self._to_float(battery):.1f} %")
            self.quick_wp.setText(
                f"{current_wp}/{mission_count}" if current_wp is not None and mission_count > 0 else "--"
            )

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

        self.telemetry_mode.setText(
            str(mode)
        )

        self.telemetry_arm.setText(
            str(armed)
        )

        if armed and not self._drone_armed:

            self._joystick_warned = False

        self._drone_armed = bool(
            armed
        )

        self._set_arm_led(
            self._drone_armed
        )

        try:

            self._drone_alt = float(
                alt
            )

        except (
            TypeError,
            ValueError,
        ):

            self._drone_alt = 0.0

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

        if distance is None:

            self.telemetry_distance.setText(
                "--"
            )

        else:

            self.telemetry_distance.setText(
                f"{self._to_float(distance):.2f} m"
            )

        if altitude_error is None:

            self.telemetry_alt_error.setText(
                "--"
            )

        else:

            self.telemetry_alt_error.setText(
                f"{self._to_float(altitude_error):.2f} m"
            )

        self.joystick_panel.sync_targets(
            status
        )

        # ----------------------------------------------------
        # Mode sync
        # ----------------------------------------------------

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
    # SYNC HELPERS
    # ========================================================

    @staticmethod
    def _sync_double_spin(
        widget,
        value,
    ):

        if value is None:

            return

        try:

            old_block = (
                widget.blockSignals(
                    True
                )
            )

            widget.setValue(
                float(value)
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

    @staticmethod
    def _sync_int_spin(
        widget,
        value,
    ):

        if value is None:

            return

        try:

            old_block = (
                widget.blockSignals(
                    True
                )
            )

            widget.setValue(
                int(value)
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

    @staticmethod
    def _sync_slider(
        widget,
        value,
        scale=1.0,
    ):

        if value is None:

            return

        try:

            old_block = (
                widget.blockSignals(
                    True
                )
            )

            widget.setValue(
                int(
                    float(value)
                    * scale
                )
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

    @staticmethod
    def _set_double_silent(
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

    @staticmethod
    def _set_slider_silent(
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
    # UTIL
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
    # WORKER RUNNING
    # ========================================================

    def _worker_running(
        self,
    ):

        return (
            self.worker is not None
            and
            self.worker.isRunning()
        )

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

        self._set_mavlink_led(False)

        self.live_frame.setEnabled(
            False
        )

        self.joystick_panel.set_enabled(
            False
        )

        self.mission_panel.set_enabled(
            False
        )

        self.start_button.setEnabled(
            True
        )

        self.stop_button.setEnabled(
            False
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event,
    ):

        # ----------------------------------------------------
        # Remove global wheel filter.
        # ----------------------------------------------------

        app = QApplication.instance()

        if (
            app is not None
            and
            self._wheel_filter is not None
        ):

            try:

                app.removeEventFilter(
                    self._wheel_filter
                )

            except Exception:

                pass

            self._wheel_filter = None

        # ----------------------------------------------------
        # Stop simulation.
        # ----------------------------------------------------

        if self.worker is not None:

            self.worker.stop()

            if self.worker.isRunning():

                self.worker.wait()

            self.worker = None

        event.accept()