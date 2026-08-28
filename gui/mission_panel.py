from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)


class MissionPanel(QGroupBox):
    """
    Lets the user build a waypoint mission and fly it
    autonomously without needing a ground station.

    Workflow:

        1. Enter lat/lon/alt/speed, click ADD WAYPOINT
           (repeat for each waypoint).
        2. Click UPLOAD TO DRONE to push the table to the
           simulator's mission.
        3. ARM the drone (see MANUAL FLIGHT CONTROL / LIVE
           SIMULATION CONTROL panels), then click
           START MISSION.

    Commands are forwarded to a plain callback attribute so
    this widget stays decoupled from SimulationWorker, in
    line with ManualControlPanel / JoystickPanel.
    """

    COLUMNS = (
        "#",
        "Latitude",
        "Longitude",
        "Altitude (m)",
        "Speed (m/s)",
        "Trạng thái",
    )

    def __init__(self, parent=None):

        super().__init__("MISSION WAYPOINTS", parent)

        self.on_command = None

        self._setup_ui()

        self.set_enabled(False)

    # ========================================================
    # UI
    # ========================================================

    def _setup_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # ----------------------------------------------------
        # WAYPOINT INPUT ROW
        # ----------------------------------------------------

        form = QGridLayout()

        form.addWidget(QLabel("Latitude"), 0, 0)
        form.addWidget(QLabel("Longitude"), 0, 1)
        form.addWidget(QLabel("Altitude (m)"), 0, 2)
        form.addWidget(QLabel("Speed (m/s)"), 0, 3)

        self.lat_input = QDoubleSpinBox()
        self.lat_input.setRange(-90.0, 90.0)
        self.lat_input.setDecimals(7)
        self.lat_input.setSingleStep(0.0001)

        self.lon_input = QDoubleSpinBox()
        self.lon_input.setRange(-180.0, 180.0)
        self.lon_input.setDecimals(7)
        self.lon_input.setSingleStep(0.0001)

        self.alt_input = QDoubleSpinBox()
        self.alt_input.setRange(0.0, 1000.0)
        self.alt_input.setDecimals(1)
        self.alt_input.setValue(10.0)

        self.speed_input = QDoubleSpinBox()
        self.speed_input.setRange(0.0, 50.0)
        self.speed_input.setDecimals(1)
        self.speed_input.setValue(5.0)

        form.addWidget(self.lat_input, 1, 0)
        form.addWidget(self.lon_input, 1, 1)
        form.addWidget(self.alt_input, 1, 2)
        form.addWidget(self.speed_input, 1, 3)

        self.add_button = QPushButton("ADD WAYPOINT")
        self.add_button.clicked.connect(
            self._add_row
        )

        self.add_rtl_button = QPushButton("ADD RTL (bay về nhà)")
        self.add_rtl_button.clicked.connect(
            self._add_rtl_row
        )

        form.addWidget(self.add_button, 1, 4)
        form.addWidget(self.add_rtl_button, 1, 5)

        layout.addLayout(form)

        # ----------------------------------------------------
        # WAYPOINT TABLE
        # ----------------------------------------------------

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.table.setMinimumHeight(260)
        self.table.setMaximumHeight(400)

        layout.addWidget(self.table)

        # ----------------------------------------------------
        # TABLE ACTIONS
        # ----------------------------------------------------

        table_actions = QHBoxLayout()

        self.remove_button = QPushButton("REMOVE SELECTED")
        self.remove_button.clicked.connect(
            self._remove_selected
        )

        self.clear_button = QPushButton("CLEAR ALL")
        self.clear_button.clicked.connect(
            self._clear_rows
        )

        table_actions.addWidget(self.remove_button)
        table_actions.addWidget(self.clear_button)

        layout.addLayout(table_actions)

        # ----------------------------------------------------
        # MISSION SPEED
        # ----------------------------------------------------

        speed_row = QHBoxLayout()

        speed_row.addWidget(
            QLabel("Tốc độ chung mission (m/s)")
        )

        self.mission_speed_input = QDoubleSpinBox()
        self.mission_speed_input.setRange(0.1, 50.0)
        self.mission_speed_input.setDecimals(1)
        self.mission_speed_input.setValue(5.0)

        speed_row.addWidget(self.mission_speed_input)

        self.apply_speed_button = QPushButton(
            "ÁP DỤNG TỐC ĐỘ"
        )
        self.apply_speed_button.clicked.connect(
            self._apply_mission_speed
        )

        speed_row.addWidget(self.apply_speed_button)

        layout.addLayout(speed_row)

        # ----------------------------------------------------
        # MISSION ACTIONS
        # ----------------------------------------------------

        mission_actions = QHBoxLayout()

        self.upload_button = QPushButton("UPLOAD TO DRONE")
        self.upload_button.clicked.connect(
            self._upload_mission
        )

        self.start_button = QPushButton("START MISSION")
        self.start_button.clicked.connect(
            self._start_mission
        )

        self.stop_button = QPushButton("STOP MISSION")
        self.stop_button.clicked.connect(
            self._stop_mission
        )

        mission_actions.addWidget(self.upload_button)
        mission_actions.addWidget(self.start_button)
        mission_actions.addWidget(self.stop_button)

        layout.addLayout(mission_actions)

        hint = QLabel(
            "Nạp waypoint rồi bấm UPLOAD TO DRONE. "
            "Drone phải ở trạng thái ARMED trước khi "
            "bấm START MISSION."
        )

        hint.setStyleSheet(
            "QLabel { color: gray; font-style: italic; }"
        )

        layout.addWidget(hint)

        self.setLayout(layout)

    # ========================================================
    # SET WAYPOINTS
    #
    # Rebuilds the table from the drone's actual mission,
    # so waypoints uploaded from an external GCS (Mission
    # Planner / QGroundControl) also show up here.
    # ========================================================

    def set_waypoints(self, payload):

        waypoints = payload.get("waypoints", [])

        current_index = payload.get("current_index", 0)

        active = payload.get("active", False)

        finished = payload.get("finished", False)

        self.table.setRowCount(0)

        for waypoint in waypoints:

            row = self.table.rowCount()

            self.table.insertRow(row)

            action = waypoint.get(
                "action",
                "waypoint",
            )

            index = waypoint.get("index", row + 1)

            if finished or index < current_index:

                status = "✓"

            elif index == current_index and active:

                status = "➤"

            else:

                status = ""

            if action == "rtl":

                values = (
                    str(index),
                    "RTL",
                    "RTL",
                    "RTL",
                    "-",
                    status,
                )

            else:

                values = (
                    str(index),
                    f"{waypoint.get('latitude', 0.0):.7f}",
                    f"{waypoint.get('longitude', 0.0):.7f}",
                    f"{waypoint.get('altitude', 0.0):.1f}",
                    f"{waypoint.get('speed', 0.0):.1f}",
                    status,
                )

            for column, text in enumerate(values):

                item = QTableWidgetItem(text)
                item.setTextAlignment(0x0084)  # AlignCenter

                self.table.setItem(row, column, item)

            self.table.item(row, 0).setData(
                Qt.UserRole,
                action,
            )

    # ========================================================
    # ADD ROW
    # ========================================================

    def _add_row(self):

        row = self.table.rowCount()

        self.table.insertRow(row)

        lat = self.lat_input.value()
        lon = self.lon_input.value()
        alt = self.alt_input.value()
        speed = self.speed_input.value()

        values = (
            str(row + 1),
            f"{lat:.7f}",
            f"{lon:.7f}",
            f"{alt:.1f}",
            f"{speed:.1f}",
            "",
        )

        for column, text in enumerate(values):

            item = QTableWidgetItem(text)
            item.setTextAlignment(0x0084)  # AlignCenter

            self.table.setItem(row, column, item)

        self.table.item(row, 0).setData(
            Qt.UserRole,
            "waypoint",
        )

    # ========================================================
    # ADD RTL ROW
    # ========================================================

    def _add_rtl_row(self):

        row = self.table.rowCount()

        self.table.insertRow(row)

        values = (
            str(row + 1),
            "RTL",
            "RTL",
            "RTL",
            "-",
            "",
        )

        for column, text in enumerate(values):

            item = QTableWidgetItem(text)
            item.setTextAlignment(0x0084)  # AlignCenter

            self.table.setItem(row, column, item)

        self.table.item(row, 0).setData(
            Qt.UserRole,
            "rtl",
        )

    # ========================================================
    # APPLY MISSION SPEED
    #
    # Sets the same speed for every waypoint in the table
    # (RTL rows excluded) and, if a mission is already
    # uploaded/running, applies it live too.
    # ========================================================

    def _apply_mission_speed(self):

        speed = self.mission_speed_input.value()

        for row in range(self.table.rowCount()):

            action = self.table.item(row, 0).data(
                Qt.UserRole
            ) or "waypoint"

            if action == "rtl":
                continue

            item = QTableWidgetItem(f"{speed:.1f}")
            item.setTextAlignment(0x0084)  # AlignCenter

            self.table.setItem(row, 4, item)

        if self.on_command is not None:

            self.on_command(
                "set_mission_speed",
                speed,
            )

    # ========================================================
    # REMOVE SELECTED
    # ========================================================

    def _remove_selected(self):

        rows = sorted(
            {
                index.row()
                for index in self.table.selectedIndexes()
            },
            reverse=True,
        )

        for row in rows:
            self.table.removeRow(row)

        self._renumber_rows()

    # ========================================================
    # CLEAR ALL
    # ========================================================

    def _clear_rows(self):

        self.table.setRowCount(0)

    # ========================================================
    # RENUMBER
    # ========================================================

    def _renumber_rows(self):

        for row in range(self.table.rowCount()):

            item = self.table.item(row, 0)

            if item is not None:
                item.setText(str(row + 1))

    # ========================================================
    # UPLOAD MISSION
    # ========================================================

    def _upload_mission(self):

        if self.on_command is None:
            return

        self.on_command("clear_mission", None)

        for row in range(self.table.rowCount()):

            action = self.table.item(row, 0).data(
                Qt.UserRole
            ) or "waypoint"

            if action == "rtl":

                waypoint = {
                    "action": "rtl",
                }

            else:

                waypoint = {
                    "action": "waypoint",
                    "latitude": float(
                        self.table.item(row, 1).text()
                    ),
                    "longitude": float(
                        self.table.item(row, 2).text()
                    ),
                    "altitude": float(
                        self.table.item(row, 3).text()
                    ),
                    "speed": float(
                        self.table.item(row, 4).text()
                    ),
                }

            self.on_command("add_waypoint", waypoint)

    # ========================================================
    # START / STOP MISSION
    # ========================================================

    def _start_mission(self):

        if self.on_command is not None:
            self.on_command("start_mission", None)

    def _stop_mission(self):

        if self.on_command is not None:
            self.on_command("stop_mission", None)

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(self, enabled):

        self.lat_input.setEnabled(enabled)
        self.lon_input.setEnabled(enabled)
        self.alt_input.setEnabled(enabled)
        self.speed_input.setEnabled(enabled)

        self.add_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)

        self.upload_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
