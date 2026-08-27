from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from gui.simulation_worker import SimulationWorker


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # ====================================================
        # WINDOW
        # ====================================================

        self.setWindowTitle(
            "RIGEL UAV Simulator"
        )

        self.setMinimumSize(
            800,
            500,
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
    # UI
    # ========================================================

    def _setup_ui(self):

        central_widget = QWidget()

        self.setCentralWidget(
            central_widget
        )

        main_layout = QVBoxLayout(
            central_widget
        )

        main_layout.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        main_layout.setSpacing(
            15
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
            }
            """
        )

        main_layout.addWidget(
            title
        )

        # ====================================================
        # SIMULATOR PANEL
        # ====================================================

        simulator_frame = QFrame()

        simulator_frame.setFrameShape(
            QFrame.StyledPanel
        )

        simulator_layout = QVBoxLayout(
            simulator_frame
        )

        simulator_layout.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        simulator_title = QLabel(
            "DRONE SIMULATOR"
        )

        simulator_title.setStyleSheet(
            """
            QLabel {
                font-size: 20px;
                font-weight: bold;
            }
            """
        )

        simulator_layout.addWidget(
            simulator_title
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
                padding: 15px;
            }
            """
        )

        simulator_layout.addWidget(
            self.status_label
        )

        # ====================================================
        # TELEMETRY
        # ====================================================

        self.telemetry_label = QLabel(
            "ALT: -- m   |   "
            "SPD: -- m/s   |   "
            "BAT: -- %"
        )

        self.telemetry_label.setAlignment(
            Qt.AlignCenter
        )

        self.telemetry_label.setStyleSheet(
            """
            QLabel {
                font-size: 16px;
                padding: 10px;
            }
            """
        )

        simulator_layout.addWidget(
            self.telemetry_label
        )

        # ====================================================
        # BUTTONS
        # ====================================================

        button_layout = QHBoxLayout()

        self.start_button = QPushButton(
            "START"
        )

        self.stop_button = QPushButton(
            "STOP"
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

        button_layout.addWidget(
            self.start_button
        )

        button_layout.addWidget(
            self.stop_button
        )

        simulator_layout.addLayout(
            button_layout
        )

        main_layout.addWidget(
            simulator_frame
        )

        # ====================================================
        # MAVLINK STATUS
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
                padding: 10px;
                font-size: 14px;
            }
            """
        )

        main_layout.addWidget(
            self.mavlink_label
        )

        # ====================================================
        # STRETCH
        # ====================================================

        main_layout.addStretch()

    # ========================================================
    # START SIMULATION
    # ========================================================

    def start_simulation(self):

        # ----------------------------------------------------
        # Prevent duplicate worker
        # ----------------------------------------------------

        if self.worker is not None:

            if self.worker.isRunning():

                return

        # ====================================================
        # DRONE CONFIG
        # ====================================================

        drone_config = {

            "lat": 10.8231000,

            "lon": 106.6297000,

            "alt": 0.0,

            "takeoff_altitude": 20.0,

            "speed": 5.0,

            "heading": 90.0,
        }

        # ====================================================
        # MAVLINK CONFIG
        # ====================================================

        mavlink_config = {

            "connection_string":
                "udpout:127.0.0.1:14550",

            "system_id": 1,

            "component_id": 1,
        }

        # ====================================================
        # CREATE WORKER
        # ====================================================

        self.worker = SimulationWorker(

            drone_config=drone_config,

            mavlink_config=mavlink_config,
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

        self.worker.error_occurred.connect(
            self.on_error
        )

        # ====================================================
        # UPDATE UI
        # ====================================================

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

        # ====================================================
        # START THREAD
        # ====================================================

        self.worker.start()

    # ========================================================
    # STOP SIMULATION
    # ========================================================

    def stop_simulation(self):

        if self.worker is None:

            return

        # ----------------------------------------------------
        # Tell worker to stop
        # ----------------------------------------------------

        self.status_label.setText(
            "Status: STOPPING..."
        )

        self.stop_button.setEnabled(
            False
        )

        self.worker.stop()

        # ----------------------------------------------------
        # Wait for thread
        # ----------------------------------------------------

        if self.worker.isRunning():

            self.worker.wait(
                2000
            )

        # ----------------------------------------------------
        # Release worker
        # ----------------------------------------------------

        self.worker = None

        # ----------------------------------------------------
        # Update UI
        # ----------------------------------------------------

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

        self.telemetry_label.setText(
            "ALT: -- m   |   "
            "SPD: -- m/s   |   "
            "BAT: -- %"
        )

    # ========================================================
    # STATUS CALLBACK
    # ========================================================

    def on_status_changed(
        self,
        status,
    ):

        if status == "RUNNING":

            self.status_label.setText(
                "Status: RUNNING"
            )

            self.mavlink_label.setText(
                "MAVLink: CONNECTED"
            )

        elif status == "STOPPED":

            self.status_label.setText(
                "Status: STOPPED"
            )

            self.mavlink_label.setText(
                "MAVLink: DISCONNECTED"
            )

    # ========================================================
    # TELEMETRY CALLBACK
    # ========================================================

    def on_telemetry_updated(
        self,
        status,
    ):

        altitude = status.get(
            "alt",
            0.0,
        )

        speed = status.get(
            "ground_speed",
            0.0,
        )

        battery = status.get(
            "battery",
            0.0,
        )

        self.telemetry_label.setText(

            f"ALT: {altitude:.2f} m   |   "
            f"SPD: {speed:.2f} m/s   |   "
            f"BAT: {battery:.1f} %"
        )

    # ========================================================
    # ERROR CALLBACK
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

        self.start_button.setEnabled(
            True
        )

        self.stop_button.setEnabled(
            False
        )

        self.worker = None

    # ========================================================
    # CLOSE WINDOW
    # ========================================================

    def closeEvent(
        self,
        event,
    ):

        if self.worker is not None:

            self.worker.stop()

            if self.worker.isRunning():

                self.worker.wait(
                    2000
                )

            self.worker = None

        event.accept()