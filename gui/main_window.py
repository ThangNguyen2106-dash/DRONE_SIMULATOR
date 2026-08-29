from PySide6.QtCore import QObject, QEvent, Qt, QThread, Signal
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
from core.version_check import check_for_update


# ============================================================
# VERSION CHECK THREAD
#
# git ls-remote can block on network I/O, so the check runs
# off the GUI thread and reports back through a signal instead
# of ever touching widgets directly.
# ============================================================

class _VersionCheckThread(QThread):

    result_ready = Signal(dict)

    def __init__(self, repo_dir, parent=None):

        super().__init__(parent)

        self.repo_dir = repo_dir

    def run(self):

        result = check_for_update(
            self.repo_dir
        )

        self.result_ready.emit(
            result
        )


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
            1200,
            850,
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

        self._start_version_check()

    # ========================================================
    # VERSION CHECK
    # ========================================================

    def _start_version_check(self):

        import os

        repo_dir = os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )

        self._version_check_thread = (
            _VersionCheckThread(
                repo_dir,
                self,
            )
        )

        self._version_check_thread.result_ready.connect(
            self._on_version_check_result
        )

        self._version_check_thread.start()

    def _on_version_check_result(self, result):

        if result.get("status") != "outdated":

            return

        branch = result.get("branch") or "?"

        local = result.get("local") or "?"

        remote = result.get("remote") or "?"

        QMessageBox.information(
            self,
            "Có bản cập nhật mới",
            "Bạn đang chạy bản cũ của simulator.\n\n"
            f"Nhánh: {branch}\n"
            f"Bản đang chạy: {local}\n"
            f"Bản mới nhất: {remote}\n\n"
            "Chạy 'git pull' để cập nhật.",
        )

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
        # STATUS (fixed top bar — stays visible while the rest
        # of the panels below scroll)
        # ====================================================

        self._create_status_panel(
            root_layout
        )

        # ====================================================
        # SCROLL AREA
        # ====================================================

        scroll = QScrollArea()

        scroll.setWidgetResizable(
            True
        )

        scroll.setAlignment(
            Qt.AlignHCenter
        )

        content = QWidget()

        # Keep the form-style panels at a readable width and
        # center them instead of stretching labels/fields
        # across a maximized ultra-wide window.
        content.setMaximumWidth(
            1400
        )

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
        # INITIAL DRONE CONFIG
        # ====================================================

        self.drone_config_panel = (
            DroneConfigPanel()
        )

        content_layout.addWidget(
            self.drone_config_panel
        )

        # ====================================================
        # MAVLINK CONFIG
        # ====================================================

        self.mavlink_config_panel = (
            MAVLinkConfigPanel()
        )

        self.mavlink_config_panel.on_debug_toggled = (
            self._on_telemetry_debug_toggled
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
        # JOYSTICK
        # ====================================================

        self.joystick_panel = (
            JoystickPanel()
        )

        self.joystick_panel.on_command = (
            self._on_joystick_command
        )

        content_layout.addWidget(
            self.joystick_panel
        )

        # ====================================================
        # MISSION
        # ====================================================

        self.mission_panel = (
            MissionPanel()
        )

        self.mission_panel.on_command = (
            self._on_mission_command
        )

        content_layout.addWidget(
            self.mission_panel
        )

        # ====================================================
        # TELEMETRY
        # ====================================================

        self._create_telemetry_panel(
            content_layout
        )

        content_layout.addStretch()

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
            NoWheelDoubleSpinBox()
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

        self.altitude_button = QPushButton(
            "APPLY"
        )

        self.altitude_button.clicked.connect(
            self.apply_altitude
        )

        self.altitude_slider.valueChanged.connect(
            self.on_altitude_slider_changed
        )

        self.altitude_slider.sliderPressed.connect(
            self._require_armed
        )

        self.altitude_spin.valueChanged.connect(
            self.on_altitude_spin_changed
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
            NoWheelDoubleSpinBox()
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

        self.speed_button = QPushButton(
            "APPLY"
        )

        self.speed_button.clicked.connect(
            self.apply_speed
        )

        self.speed_slider.valueChanged.connect(
            self.on_speed_slider_changed
        )

        self.speed_slider.sliderPressed.connect(
            self._require_armed
        )

        self.speed_spin.valueChanged.connect(
            self.on_speed_spin_changed
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
            NoWheelDoubleSpinBox()
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

        self.heading_button = QPushButton(
            "APPLY"
        )

        self.heading_button.clicked.connect(
            self.apply_heading
        )

        self.heading_slider.valueChanged.connect(
            self.on_heading_slider_changed
        )

        self.heading_slider.sliderPressed.connect(
            self._require_armed
        )

        self.heading_spin.valueChanged.connect(
            self.on_heading_spin_changed
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
            NoWheelDoubleSpinBox()
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

        self.latitude_button.clicked.connect(
            self.apply_latitude
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
            NoWheelDoubleSpinBox()
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

        self.longitude_button.clicked.connect(
            self.apply_longitude
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
            NoWheelDoubleSpinBox()
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
            NoWheelDoubleSpinBox()
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
            NoWheelDoubleSpinBox()
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
            NoWheelDoubleSpinBox()
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

        self.gps_fix_spin = (
            NoWheelSpinBox()
        )

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

        self.satellites_spin = (
            NoWheelSpinBox()
        )

        self.satellites_spin.setRange(
            0,
            255,
        )

        self.satellites_spin.setValue(
            12
        )

        self.gps_button = QPushButton(
            "APPLY GPS"
        )

        self.gps_button.clicked.connect(
            self.apply_gps
        )

        layout.addWidget(
            self.satellites_spin,
            row,
            1,
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
            NoWheelDoubleSpinBox()
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
            NoWheelDoubleSpinBox()
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

        row += 1

        # ====================================================
        # ACTION BUTTONS
        # ====================================================

        actions = QHBoxLayout()

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

        self.set_home_button = QPushButton(
            "SET HOME = HERE"
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

        self.set_home_button.clicked.connect(
            self.set_home_here
        )

        actions.addWidget(
            self.arm_button
        )

        actions.addWidget(
            self.disarm_button
        )

        actions.addWidget(
            self.takeoff_button
        )

        actions.addWidget(
            self.land_button
        )

        actions.addWidget(
            self.rtl_button
        )

        actions.addWidget(
            self.set_home_button
        )

        layout.addLayout(
            actions,
            row,
            0,
            1,
            3,
        )

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

        self.worker.queue_command(
            "takeoff",
            self.altitude_spin.value(),
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

        # ----------------------------------------------------
        # Sync controls without generating commands.
        # ----------------------------------------------------

        self._sync_double_spin(
            self.altitude_spin,
            status.get(
                "target_altitude"
            ),
        )

        self._sync_double_spin(
            self.speed_spin,
            status.get(
                "target_ground_speed"
            ),
        )

        self._sync_double_spin(
            self.heading_spin,
            status.get(
                "target_heading"
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

        self._sync_int_spin(
            self.gps_fix_spin,
            status.get(
                "gps_fix"
            ),
        )

        self._sync_int_spin(
            self.satellites_spin,
            status.get(
                "satellites"
            ),
        )

        self._sync_double_spin(
            self.hdop_spin,
            status.get(
                "gps_hdop"
            ),
        )

        self._sync_double_spin(
            self.vdop_spin,
            status.get(
                "gps_vdop"
            ),
        )

        # ----------------------------------------------------
        # Slider sync
        # ----------------------------------------------------

        self._sync_slider(
            self.altitude_slider,
            status.get(
                "target_altitude"
            ),
            100.0,
        )

        self._sync_slider(
            self.speed_slider,
            status.get(
                "target_ground_speed"
            ),
            100.0,
        )

        self._sync_slider(
            self.heading_slider,
            status.get(
                "target_heading"
            ),
            100.0,
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
        # Stop the version-check thread if still running.
        # ----------------------------------------------------

        thread = getattr(
            self, "_version_check_thread", None
        )

        if thread is not None and thread.isRunning():

            thread.wait(100)

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