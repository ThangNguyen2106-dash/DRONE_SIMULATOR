from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)


class ManualControlPanel(QGroupBox):
    """
    Manual ARM / DISARM / TAKEOFF / LAND / RTL buttons, so the
    simulator can be flown standalone without a GCS connected.

    Like FailurePanel, this only makes sense while a simulation
    is running - it starts disabled and main_window enables it
    once the worker is up. Button clicks are forwarded to
    plain callback attributes so this widget stays decoupled
    from SimulationWorker / FlightController.
    """

    def __init__(self, parent=None):

        super().__init__(
            "MANUAL FLIGHT CONTROL",
            parent,
        )

        self.on_arm = None
        self.on_disarm = None
        self.on_takeoff = None
        self.on_land = None
        self.on_rtl = None

        self._setup_ui()

        self.set_enabled(False)

    # ========================================================
    # UI
    # ========================================================

    def _setup_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(15, 15, 15, 15)

        layout.setSpacing(10)

        row = QHBoxLayout()

        self.arm_button = QPushButton("ARM")
        self.disarm_button = QPushButton("DISARM")
        self.takeoff_button = QPushButton("TAKEOFF")
        self.land_button = QPushButton("LAND")
        self.rtl_button = QPushButton("RTL")

        self.arm_button.clicked.connect(self._arm_clicked)
        self.disarm_button.clicked.connect(self._disarm_clicked)
        self.takeoff_button.clicked.connect(self._takeoff_clicked)
        self.land_button.clicked.connect(self._land_clicked)
        self.rtl_button.clicked.connect(self._rtl_clicked)

        for button in (
            self.arm_button,
            self.disarm_button,
            self.takeoff_button,
            self.land_button,
            self.rtl_button,
        ):
            row.addWidget(button)

        layout.addLayout(row)

        self.setLayout(layout)

    # ========================================================
    # HANDLERS
    # ========================================================

    def _arm_clicked(self):
        if self.on_arm is not None:
            self.on_arm()

    def _disarm_clicked(self):
        if self.on_disarm is not None:
            self.on_disarm()

    def _takeoff_clicked(self):
        if self.on_takeoff is not None:
            self.on_takeoff()

    def _land_clicked(self):
        if self.on_land is not None:
            self.on_land()

    def _rtl_clicked(self):
        if self.on_rtl is not None:
            self.on_rtl()

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(self, enabled):

        self.arm_button.setEnabled(enabled)
        self.disarm_button.setEnabled(enabled)
        self.takeoff_button.setEnabled(enabled)
        self.land_button.setEnabled(enabled)
        self.rtl_button.setEnabled(enabled)
