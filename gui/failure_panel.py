from PySide6.QtWidgets import (
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QCheckBox,
    QDoubleSpinBox,
    QLabel,
)


class FailurePanel(QGroupBox):
    """
    Live fault-injection and wind panel.

    Only meaningful while a simulation is running, so it starts
    disabled and main_window enables it once the worker is up.
    Every control applies immediately - there is no Apply button,
    since the point is to be able to toggle a fault mid-flight
    and watch the GCS react.
    """

    def __init__(self, parent=None):

        super().__init__(
            "FAILURE SIMULATION & WIND",
            parent,
        )

        # Callback hooks, wired up by main_window. Kept as plain
        # attributes (instead of Qt signals) so this panel has
        # zero knowledge of SimulationWorker.

        self.on_gps_failure = None
        self.on_compass_failure = None
        self.on_rc_failure = None
        self.on_ekf_failure = None
        self.on_wind_changed = None

        self._setup_ui()

        self.set_enabled(False)

    # ========================================================
    # UI
    # ========================================================

    def _setup_ui(self):

        layout = QFormLayout()

        layout.setContentsMargins(15, 15, 15, 15)

        layout.setSpacing(10)

        # ----------------------------------------------------
        # Failure checkboxes
        # ----------------------------------------------------

        checkbox_row = QHBoxLayout()

        self.gps_failure_box = QCheckBox("GPS")
        self.compass_failure_box = QCheckBox("Compass")
        self.rc_failure_box = QCheckBox("RC Link")
        self.ekf_failure_box = QCheckBox("EKF")

        self.gps_failure_box.toggled.connect(self._gps_toggled)
        self.compass_failure_box.toggled.connect(self._compass_toggled)
        self.rc_failure_box.toggled.connect(self._rc_toggled)
        self.ekf_failure_box.toggled.connect(self._ekf_toggled)

        checkbox_row.addWidget(self.gps_failure_box)
        checkbox_row.addWidget(self.compass_failure_box)
        checkbox_row.addWidget(self.rc_failure_box)
        checkbox_row.addWidget(self.ekf_failure_box)

        layout.addRow(
            "Inject Failure:",
            checkbox_row,
        )

        # ----------------------------------------------------
        # Wind
        # ----------------------------------------------------

        self.wind_speed = QDoubleSpinBox()
        self.wind_speed.setDecimals(1)
        self.wind_speed.setRange(0.0, 30.0)
        self.wind_speed.setSingleStep(0.5)
        self.wind_speed.setSuffix(" m/s")
        self.wind_speed.valueChanged.connect(self._wind_changed)

        layout.addRow(
            "Wind Speed:",
            self.wind_speed,
        )

        self.wind_direction = QDoubleSpinBox()
        self.wind_direction.setDecimals(0)
        self.wind_direction.setRange(0.0, 359.0)
        self.wind_direction.setSingleStep(15.0)
        self.wind_direction.setSuffix(" °  (from)")
        self.wind_direction.valueChanged.connect(self._wind_changed)

        layout.addRow(
            "Wind Direction:",
            self.wind_direction,
        )

        hint = QLabel(
            "Applies live while the simulation is running."
        )

        hint.setStyleSheet("QLabel { font-size: 11px; }")

        layout.addRow(hint)

        self.setLayout(layout)

    # ========================================================
    # HANDLERS
    # ========================================================

    def _gps_toggled(self, checked):
        if self.on_gps_failure is not None:
            self.on_gps_failure(checked)

    def _compass_toggled(self, checked):
        if self.on_compass_failure is not None:
            self.on_compass_failure(checked)

    def _rc_toggled(self, checked):
        if self.on_rc_failure is not None:
            self.on_rc_failure(checked)

    def _ekf_toggled(self, checked):
        if self.on_ekf_failure is not None:
            self.on_ekf_failure(checked)

    def _wind_changed(self, _value):
        if self.on_wind_changed is not None:
            self.on_wind_changed(
                self.wind_speed.value(),
                self.wind_direction.value(),
            )

    # ========================================================
    # RESET
    #
    # Called when a new simulation starts so stale faults from
    # a previous run don't silently carry over.
    # ========================================================

    def reset(self):

        for box in (
            self.gps_failure_box,
            self.compass_failure_box,
            self.rc_failure_box,
            self.ekf_failure_box,
        ):
            box.blockSignals(True)
            box.setChecked(False)
            box.blockSignals(False)

        self.wind_speed.blockSignals(True)
        self.wind_speed.setValue(0.0)
        self.wind_speed.blockSignals(False)

        self.wind_direction.blockSignals(True)
        self.wind_direction.setValue(0.0)
        self.wind_direction.blockSignals(False)

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(self, enabled):

        self.gps_failure_box.setEnabled(enabled)
        self.compass_failure_box.setEnabled(enabled)
        self.rc_failure_box.setEnabled(enabled)
        self.ekf_failure_box.setEnabled(enabled)
        self.wind_speed.setEnabled(enabled)
        self.wind_direction.setEnabled(enabled)
