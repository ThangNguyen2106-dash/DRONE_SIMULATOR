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
        "Loại",
        "Latitude",
        "Longitude",
        "Altitude (m)",
        "Speed (m/s)",
        "Trạng thái",
    )

    # Waypoint.action -> table label. Covers every action a
    # GCS-uploaded mission (Mission Planner / QGroundControl)
    # can currently produce, not just what the GUI's own ADD
    # WAYPOINT / ADD RTL buttons create.
    ACTION_LABELS = {
        "waypoint": "WAYPOINT",
        "takeoff": "TAKEOFF",
        "land": "LAND",
        "loiter": "DELAY",
        "delay": "DELAY",
        "rtl": "RTL",
    }

    def __init__(self, parent=None):

        super().__init__("MISSION WAYPOINTS", parent)

        self.on_command = None

        # True whenever the table has local changes (added
        # row, RTL row, edited cell, removed row, ...) not yet
        # pushed to the drone via UPLOAD TO DRONE. While dirty,
        # incoming mission_updated syncs (e.g. progress ticks
        # while a previously-uploaded mission is flying) must
        # not rebuild the table, or the unsaved edits vanish.
        self._dirty = False

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
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
        )
        self.table.setMinimumHeight(260)
        self.table.setMaximumHeight(400)

        self._syncing_table = False

        self.table.itemChanged.connect(
            self._on_item_changed
        )

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
    # MAKE TABLE ITEM
    #
    # editable=False is used for the "#" / "Trạng thái" columns
    # and for every column of an RTL row (RTL has no lat/lon/
    # alt/speed of its own — it always resolves to home).
    # ========================================================

    def _make_item(self, text, editable, value=None):

        item = QTableWidgetItem(text)
        item.setTextAlignment(0x0084)  # AlignCenter

        if not editable:

            item.setFlags(
                item.flags() & ~Qt.ItemIsEditable
            )

        elif value is not None:

            # Known-good numeric value, used by
            # _on_item_changed() to restore this cell if the
            # user later types something unparseable.

            item.setData(Qt.UserRole + 1, value)

        return item

    # ========================================================
    # ITEM CHANGED (inline table editing)
    #
    # Only reformats/validates the cell in place. Pushing the
    # new value down to the drone still requires UPLOAD TO
    # DRONE, same as adding a row from the input fields above —
    # keeps a single, predictable "edit then upload" workflow.
    # ========================================================

    def _on_item_changed(self, item):

        if self._syncing_table:
            return

        self._dirty = True

        column = item.column()

        # Only the numeric columns (Latitude, Longitude,
        # Altitude, Speed) are ever editable — "#" / "Loại" /
        # "Trạng thái" and RTL-row cells are flagged
        # non-editable, so this only has to validate/reformat
        # numbers.

        if column not in (2, 3, 4, 5):
            return

        decimals = 7 if column in (2, 3) else 1

        # Accept ',' as a decimal separator too — Vietnamese
        # keyboards/locale commonly type "10,5" instead of
        # "10.5", and float() rejects that outright.

        raw = item.text().strip().replace(",", ".")

        try:
            value = float(raw)

        except ValueError:

            # Invalid input (empty, stray text, ...): restore
            # the last known-good value instead of silently
            # zeroing it out — a reset to 0.0 reads as "my edit
            # didn't save" rather than "that input was invalid".

            previous = item.data(Qt.UserRole + 1)

            value = (
                previous
                if previous is not None
                else 0.0
            )

        self._syncing_table = True

        item.setText(f"{value:.{decimals}f}")
        item.setData(Qt.UserRole + 1, value)

        self._syncing_table = False

    # ========================================================
    # SET WAYPOINTS
    #
    # Rebuilds the table from the drone's actual mission,
    # so waypoints uploaded from an external GCS (Mission
    # Planner / QGroundControl) also show up here.
    # ========================================================

    def set_waypoints(self, payload):

        # Local edits (added/removed/edited rows) not yet
        # pushed via UPLOAD TO DRONE take priority over a sync
        # from the drone's real mission — otherwise a progress
        # tick while a previously-uploaded mission is flying
        # (waypoint reached, RTL step, ...) would silently wipe
        # out whatever the user is mid-editing in the table.
        if self._dirty:
            return

        self._syncing_table = True

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

            type_label = self.ACTION_LABELS.get(
                action,
                action.upper(),
            )

            numeric_values = (
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )

            if action == "rtl":

                values = (
                    str(index),
                    type_label,
                    "RTL",
                    "RTL",
                    "RTL",
                    "-",
                    status,
                )

            else:

                lat = waypoint.get("latitude", 0.0)
                lon = waypoint.get("longitude", 0.0)
                alt = waypoint.get("altitude", 0.0)
                speed = waypoint.get("speed", 0.0)

                # DELAY / LOITER (MAV_CMD_NAV_DELAY,
                # MAV_CMD_CONDITION_DELAY, MAV_CMD_NAV_LOITER_TIME)
                # have no meaningful ground speed of their own —
                # show how long they hold instead, same idea as
                # RTL's "-".
                if action in ("loiter", "delay"):

                    hold_time = waypoint.get(
                        "hold_time", 0.0
                    )

                    speed_text = f"{hold_time:.1f}s"

                else:

                    speed_text = f"{speed:.1f}"

                values = (
                    str(index),
                    type_label,
                    f"{lat:.7f}",
                    f"{lon:.7f}",
                    f"{alt:.1f}",
                    speed_text,
                    status,
                )

                numeric_values = (
                    None,
                    None,
                    lat,
                    lon,
                    alt,
                    speed if action not in ("loiter", "delay") else None,
                    None,
                )

            for column, text in enumerate(values):

                editable = (
                    column in (2, 3, 4, 5)
                    and action not in ("rtl", "loiter")
                )

                item = self._make_item(
                    text,
                    editable,
                    numeric_values[column],
                )

                self.table.setItem(row, column, item)

            self.table.item(row, 0).setData(
                Qt.UserRole,
                action,
            )

        self._syncing_table = False

    # ========================================================
    # ADD ROW
    # ========================================================

    def _add_row(self):

        self._syncing_table = True

        row = self.table.rowCount()

        self.table.insertRow(row)

        lat = self.lat_input.value()
        lon = self.lon_input.value()
        alt = self.alt_input.value()
        speed = self.speed_input.value()

        values = (
            str(row + 1),
            "WAYPOINT",
            f"{lat:.7f}",
            f"{lon:.7f}",
            f"{alt:.1f}",
            f"{speed:.1f}",
            "",
        )

        numeric_values = (
            None, None, lat, lon, alt, speed, None,
        )

        for column, text in enumerate(values):

            item = self._make_item(
                text,
                column in (2, 3, 4, 5),
                numeric_values[column],
            )

            self.table.setItem(row, column, item)

        self.table.item(row, 0).setData(
            Qt.UserRole,
            "waypoint",
        )

        self._syncing_table = False

        self._dirty = True

    # ========================================================
    # ADD RTL ROW
    # ========================================================

    def _add_rtl_row(self):

        self._syncing_table = True

        row = self.table.rowCount()

        self.table.insertRow(row)

        values = (
            str(row + 1),
            "RTL",
            "RTL",
            "RTL",
            "RTL",
            "-",
            "",
        )

        for column, text in enumerate(values):

            item = self._make_item(text, False)

            self.table.setItem(row, column, item)

        self.table.item(row, 0).setData(
            Qt.UserRole,
            "rtl",
        )

        self._syncing_table = False

        self._dirty = True

    # ========================================================
    # APPLY MISSION SPEED
    #
    # Sets the same speed for every waypoint in the table
    # (RTL rows excluded) and, if a mission is already
    # uploaded/running, applies it live too.
    # ========================================================

    def _apply_mission_speed(self):

        speed = self.mission_speed_input.value()

        self._syncing_table = True

        for row in range(self.table.rowCount()):

            action = self.table.item(row, 0).data(
                Qt.UserRole
            ) or "waypoint"

            if action in ("rtl", "loiter"):
                continue

            item = self._make_item(
                f"{speed:.1f}",
                True,
                speed,
            )

            self.table.setItem(row, 5, item)

        self._syncing_table = False

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

        self._dirty = True

    # ========================================================
    # CLEAR ALL
    # ========================================================

    def _clear_rows(self):

        self.table.setRowCount(0)

        if self.on_command is not None:

            self.on_command("clear_mission", None)

        # The drone's mission is now empty too, matching the
        # table exactly — safe to resume syncing from it (this
        # was left as `_dirty = True` before, which permanently
        # blocked set_waypoints() from ever repopulating the
        # table again, so missions uploaded afterward from an
        # external GCS never showed up).

        self._dirty = False

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

            elif action in ("loiter", "delay"):

                # The Speed column shows the delay duration as
                # e.g. "3.0s" for a DELAY row (see set_waypoints).

                hold_text = (
                    self.table.item(row, 5)
                    .text()
                    .rstrip("s")
                )

                waypoint = {
                    "action": action,
                    "latitude": float(
                        self.table.item(row, 2).text()
                    ),
                    "longitude": float(
                        self.table.item(row, 3).text()
                    ),
                    "altitude": float(
                        self.table.item(row, 4).text()
                    ),
                    "hold_time": float(hold_text),
                }

            else:

                waypoint = {
                    "action": action,
                    "latitude": float(
                        self.table.item(row, 2).text()
                    ),
                    "longitude": float(
                        self.table.item(row, 3).text()
                    ),
                    "altitude": float(
                        self.table.item(row, 4).text()
                    ),
                    "speed": float(
                        self.table.item(row, 5).text()
                    ),
                }

            self.on_command("add_waypoint", waypoint)

        # The drone's mission now matches the table exactly —
        # future mission_updated syncs (progress ticks) are
        # safe to rebuild the table from again.
        self._dirty = False

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
