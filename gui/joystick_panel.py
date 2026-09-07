import math

from PySide6.QtCore import Qt, QTimer, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
    QFrame,
)


# ============================================================
# VIRTUAL JOYSTICK WIDGET
# ============================================================

class JoystickWidget(QWidget):
    """On-screen virtual joystick.

    Drag the knob with the mouse; it springs back to the center on release.
    Emits normalized axis values in [-1.0, 1.0], with +y meaning "up" (forward).
    """

    moved = Signal(float, float)

    def __init__(self, parent=None, diameter=130):
        super().__init__(parent)
        self._diameter = diameter
        self._knob_radius = 16
        self._max_travel = diameter / 2 - self._knob_radius - 4
        self._x = 0.0
        self._y = 0.0
        self._dragging = False
        self.setFixedSize(diameter, diameter)
        self.setCursor(Qt.OpenHandCursor)

    def value(self):
        return self._x, self._y

    def set_value(self, x, y):
        self._x = max(-1.0, min(1.0, float(x)))
        self._y = max(-1.0, min(1.0, float(y)))
        self.update()
        self.moved.emit(self._x, self._y)

    def _center(self):
        return QPointF(self.width() / 2, self.height() / 2)

    def _set_from_widget_pos(self, pos):
        center = self._center()
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        distance = math.hypot(dx, dy)

        if distance > self._max_travel and distance > 0:
            scale = self._max_travel / distance
            dx *= scale
            dy *= scale

        self._x = dx / self._max_travel
        self._y = -dy / self._max_travel
        self.update()
        self.moved.emit(self._x, self._y)

    def reset(self):
        self._x = 0.0
        self._y = 0.0
        self.update()
        self.moved.emit(0.0, 0.0)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        self._set_from_widget_pos(event.position())

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        self._set_from_widget_pos(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)
        self.reset()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self._center()

        # Base circle
        painter.setPen(QPen(QColor(60, 85, 115), 2))
        painter.setBrush(QBrush(QColor(16, 24, 34)))
        painter.drawEllipse(center, self._diameter / 2 - 2, self._diameter / 2 - 2)

        # Concentric guide rings
        painter.setPen(QPen(QColor(35, 55, 75, 120), 1, Qt.PenStyle.DashLine))
        painter.drawEllipse(center, self._max_travel * 0.5, self._max_travel * 0.5)

        # 8-Direction radial crosshair
        painter.setPen(QPen(QColor(45, 68, 92), 1))
        # Horizontal & Vertical
        painter.drawLine(4, int(center.y()), self.width() - 4, int(center.y()))
        painter.drawLine(int(center.x()), 4, int(center.x()), self.height() - 4)

        # Diagonal 45 deg lines
        diag_d = self._diameter * 0.32
        cx, cy = center.x(), center.y()
        painter.drawLine(int(cx - diag_d), int(cy - diag_d), int(cx + diag_d), int(cy + diag_d))
        painter.drawLine(int(cx - diag_d), int(cy + diag_d), int(cx + diag_d), int(cy - diag_d))

        # Knob
        knob_pos = QPointF(
            center.x() + self._x * self._max_travel,
            center.y() - self._y * self._max_travel,
        )

        painter.setPen(QPen(QColor(0, 210, 255), 2))
        painter.setBrush(QBrush(QColor(0, 160, 230, 220)))
        painter.drawEllipse(knob_pos, self._knob_radius, self._knob_radius)


# ============================================================
# JOYSTICK PANEL (8-DIRECTION HOLONOMIC FLIGHT)
# ============================================================

class JoystickPanel(QGroupBox):
    """Dual virtual joysticks and 8-direction D-pad for omnidirectional drone flight:

      LEFT stick   -> X: Yaw turn rate   Y: Climb / Descend rate
      RIGHT stick  -> X: Roll (Strafe L/R) Y: Pitch (Move Fwd/Back)
      8-WAY D-PAD  -> Direct 8-directional vector buttons (↑ ↗ → ↘ ↓ ↙ ← ↖ ⏹)
      KEYBOARD     -> [W/S] Pitch, [A/D] Roll, [Q/E] Yaw, [R/F] Alt, [Space] Brake
    """

    MAX_YAW_RATE = 60.0
    MAX_CLIMB_RATE = 3.0
    MAX_SPEED = 15.0
    MAX_TILT_ANGLE = 30.0
    TICK_MS = 40
    DEADZONE = 0.05

    def __init__(self, parent=None):
        super().__init__("8-DIRECTIONAL FLIGHT & JOYSTICK CONTROL", parent)

        self.on_command = None
        self.target_altitude = 0.0
        self.target_heading = 0.0

        # Keyboard state tracking
        self._keys_pressed = set()

        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.set_enabled(False)

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Top row: Left Joystick | 8-Direction D-Pad | Right Joystick
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # ----------------------------------------------------
        # 1. LEFT STICK: YAW / ALTITUDE
        # ----------------------------------------------------
        left_box = QVBoxLayout()
        left_label = QLabel("YAW / ALTITUDE")
        left_label.setAlignment(Qt.AlignCenter)
        left_label.setStyleSheet("font-weight: bold; color: #9bb0c3; font-size: 8pt;")

        self.left_stick = JoystickWidget()
        self.left_readout = QLabel("yaw: 0.0 °/s   climb: 0.0 m/s")
        self.left_readout.setAlignment(Qt.AlignCenter)
        self.left_readout.setStyleSheet("color: #78909c; font-family: Consolas; font-size: 8pt;")

        left_box.addWidget(left_label)
        left_box.addWidget(self.left_stick, 0, Qt.AlignCenter)
        left_box.addWidget(self.left_readout)
        top_row.addLayout(left_box)

        # ----------------------------------------------------
        # 2. CENTER: 8-DIRECTIONAL D-PAD
        # ----------------------------------------------------
        dpad_box = QVBoxLayout()
        dpad_label = QLabel("8-WAY FLIGHT D-PAD")
        dpad_label.setAlignment(Qt.AlignCenter)
        dpad_label.setStyleSheet("font-weight: bold; color: #00d2ff; font-size: 8pt;")
        dpad_box.addWidget(dpad_label)

        dpad_grid = QGridLayout()
        dpad_grid.setSpacing(4)

        # 8-Direction Buttons definition: (label, direction, row, col)
        directions = [
            ("↖", "FORWARD_LEFT", 0, 0),
            ("↑", "FORWARD", 0, 1),
            ("↗", "FORWARD_RIGHT", 0, 2),
            ("←", "LEFT", 1, 0),
            ("⏹", "STOP", 1, 1),
            ("→", "RIGHT", 1, 2),
            ("↙", "BACKWARD_LEFT", 2, 0),
            ("↓", "BACKWARD", 2, 1),
            ("↘", "BACKWARD_RIGHT", 2, 2),
        ]

        self.dpad_buttons = {}
        for text, dname, r, c in directions:
            btn = QPushButton(text)
            btn.setFixedSize(36, 32)
            btn.setStyleSheet("""
                QPushButton {
                    background: #192636;
                    color: #dce6f2;
                    border: 1px solid #2f455d;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 11pt;
                }
                QPushButton:hover {
                    background: #23374d;
                    border-color: #00d2ff;
                    color: #00d2ff;
                }
                QPushButton:pressed {
                    background: #00d2ff;
                    color: #000000;
                }
            """)
            if dname == "STOP":
                btn.setStyleSheet(btn.styleSheet() + "QPushButton { color: #ff5252; }")
                btn.clicked.connect(self._on_stop_clicked)
            else:
                btn.pressed.connect(lambda d=dname: self._on_dpad_pressed(d))
                btn.released.connect(self._on_dpad_released)

            dpad_grid.addWidget(btn, r, c)
            self.dpad_buttons[dname] = btn

        dpad_box.addLayout(dpad_grid)

        self.dpad_status = QLabel("HOVER / READY")
        self.dpad_status.setAlignment(Qt.AlignCenter)
        self.dpad_status.setStyleSheet("color: #00e676; font-family: Consolas; font-size: 8pt; font-weight: bold;")
        dpad_box.addWidget(self.dpad_status)

        top_row.addLayout(dpad_box)

        # ----------------------------------------------------
        # 3. RIGHT STICK: TILT (PITCH & ROLL)
        # ----------------------------------------------------
        right_box = QVBoxLayout()
        right_label = QLabel("TILT (ROLL / PITCH)")
        right_label.setAlignment(Qt.AlignCenter)
        right_label.setStyleSheet("font-weight: bold; color: #9bb0c3; font-size: 8pt;")

        self.right_stick = JoystickWidget()
        self.right_readout = QLabel("roll: 0.0°   pitch: 0.0°")
        self.right_readout.setAlignment(Qt.AlignCenter)
        self.right_readout.setStyleSheet("color: #78909c; font-family: Consolas; font-size: 8pt;")

        right_box.addWidget(right_label)
        right_box.addWidget(self.right_stick, 0, Qt.AlignCenter)
        right_box.addWidget(self.right_readout)
        top_row.addLayout(right_box)

        main_layout.addLayout(top_row)

        # Keyboard shortcuts quick reference banner
        kb_hint = QLabel(
            "⌨ Bàn phím: [WASD / Numpad 8-2-4-6 / Mũi tên] Tiến-Lùi-Trái-Phải · [Q/E] Xoay đầu Yaw · [R/F hoặc +/-] Lên/Xuống · [Space / Num 5] Phanh"
        )
        kb_hint.setAlignment(Qt.AlignCenter)
        kb_hint.setStyleSheet("color: #9bb0c3; background: #101a26; padding: 4px; border-radius: 4px; font-size: 8pt;")
        main_layout.addWidget(kb_hint)

        self.setLayout(main_layout)

    # ========================================================
    # D-PAD BUTTON HANDLERS
    # ========================================================

    def _on_dpad_pressed(self, direction):
        if not self.isEnabled():
            return
        diag = 0.7071
        spd = 8.0
        vec_map = {
            "FORWARD": (spd, 0.0),
            "BACKWARD": (-spd, 0.0),
            "LEFT": (0.0, -spd),
            "RIGHT": (0.0, spd),
            "FORWARD_LEFT": (spd * diag, -spd * diag),
            "FORWARD_RIGHT": (spd * diag, spd * diag),
            "BACKWARD_LEFT": (-spd * diag, -spd * diag),
            "BACKWARD_RIGHT": (-spd * diag, spd * diag),
        }
        if direction in vec_map:
            fwd, lat = vec_map[direction]
            self.right_stick.set_value(lat / self.MAX_SPEED, fwd / self.MAX_SPEED)
            self.dpad_status.setText(f"FLYING: {direction}")
            self.dpad_status.setStyleSheet("color: #00d2ff; font-family: Consolas; font-size: 8pt; font-weight: bold;")

    def _on_dpad_released(self):
        self.right_stick.reset()
        self.dpad_status.setText("HOVER / BRAKING")
        self.dpad_status.setStyleSheet("color: #ffb300; font-family: Consolas; font-size: 8pt; font-weight: bold;")

    def _on_stop_clicked(self):
        self.right_stick.reset()
        self.left_stick.reset()
        self._emit("brake", None)
        self.dpad_status.setText("BRAKE / HOVER")
        self.dpad_status.setStyleSheet("color: #ff5252; font-family: Consolas; font-size: 8pt; font-weight: bold;")

    # ========================================================
    # KEYBOARD PROCESSING
    # ========================================================

    def handle_key_event(self, key_code, is_press):
        """Called by MainWindow to process keyboard flight hotkeys."""
        if not self.isEnabled():
            return False

        if is_press:
            self._keys_pressed.add(key_code)
        else:
            self._keys_pressed.discard(key_code)

        # Calculate stick values from active pressed keys
        fwd = 0.0
        lat = 0.0
        yaw = 0.0
        climb = 0.0

        # Forward (Tiến): W, Up Arrow, Numpad 8
        if (
            Qt.Key.Key_W in self._keys_pressed
            or Qt.Key.Key_Up in self._keys_pressed
            or Qt.Key.Key_8 in self._keys_pressed
        ):
            fwd += 1.0

        # Backward (Lùi): S, Down Arrow, Numpad 2
        if (
            Qt.Key.Key_S in self._keys_pressed
            or Qt.Key.Key_Down in self._keys_pressed
            or Qt.Key.Key_2 in self._keys_pressed
        ):
            fwd -= 1.0

        # Strafe Right (Tạt / Quay phải): D, Right Arrow, Numpad 6
        if (
            Qt.Key.Key_D in self._keys_pressed
            or Qt.Key.Key_Right in self._keys_pressed
            or Qt.Key.Key_6 in self._keys_pressed
        ):
            lat += 1.0

        # Strafe Left (Tạt / Quay trái): A, Left Arrow, Numpad 4
        if (
            Qt.Key.Key_A in self._keys_pressed
            or Qt.Key.Key_Left in self._keys_pressed
            or Qt.Key.Key_4 in self._keys_pressed
        ):
            lat -= 1.0

        # Numpad Direct 8-Way Diagonals (7, 9, 1, 3)
        if Qt.Key.Key_7 in self._keys_pressed:  # Forward-Left
            fwd += 0.7071
            lat -= 0.7071
        if Qt.Key.Key_9 in self._keys_pressed:  # Forward-Right
            fwd += 0.7071
            lat += 0.7071
        if Qt.Key.Key_1 in self._keys_pressed:  # Backward-Left
            fwd -= 0.7071
            lat -= 0.7071
        if Qt.Key.Key_3 in self._keys_pressed:  # Backward-Right
            fwd -= 0.7071
            lat += 0.7071

        # Yaw Rotation (Xoay đầu): Q (Trái) / E (Phải)
        if Qt.Key.Key_E in self._keys_pressed:
            yaw += 1.0
        if Qt.Key.Key_Q in self._keys_pressed:
            yaw -= 1.0

        # Altitude (Lên / Xuống): R / PageUp / Numpad +, F / PageDown / Numpad -
        if (
            Qt.Key.Key_R in self._keys_pressed
            or Qt.Key.Key_PageUp in self._keys_pressed
            or Qt.Key.Key_Plus in self._keys_pressed
        ):
            climb += 1.0
        if (
            Qt.Key.Key_F in self._keys_pressed
            or Qt.Key.Key_PageDown in self._keys_pressed
            or Qt.Key.Key_Minus in self._keys_pressed
        ):
            climb -= 1.0

        # Emergency Brake / Stop: Space, Numpad 5
        if Qt.Key.Key_Space in self._keys_pressed or Qt.Key.Key_5 in self._keys_pressed:
            self._on_stop_clicked()
            return True

        # Normalize diagonal magnitude so diagonal speed isn't 1.414x
        mag = math.hypot(lat, fwd)
        if mag > 1.0:
            lat /= mag
            fwd /= mag

        self.right_stick.set_value(lat, fwd)
        self.left_stick.set_value(yaw, climb)

        if fwd != 0.0 or lat != 0.0:
            dir_str = "8-WAY MOVE"
            if fwd > 0 and lat == 0: dir_str = "FORWARD"
            elif fwd < 0 and lat == 0: dir_str = "BACKWARD"
            elif lat < 0 and fwd == 0: dir_str = "STRAFE LEFT"
            elif lat > 0 and fwd == 0: dir_str = "STRAFE RIGHT"
            elif fwd > 0 and lat < 0: dir_str = "FORWARD-LEFT"
            elif fwd > 0 and lat > 0: dir_str = "FORWARD-RIGHT"
            elif fwd < 0 and lat < 0: dir_str = "BACKWARD-LEFT"
            elif fwd < 0 and lat > 0: dir_str = "BACKWARD-RIGHT"
            self.dpad_status.setText(f"KB: {dir_str}")
            self.dpad_status.setStyleSheet("color: #00d2ff; font-family: Consolas; font-size: 8pt; font-weight: bold;")
        elif not self._keys_pressed:
            self.dpad_status.setText("HOVER / READY")
            self.dpad_status.setStyleSheet("color: #00e676; font-family: Consolas; font-size: 8pt; font-weight: bold;")

        return True

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(self, enabled):
        was_enabled = self.left_stick.isEnabled()

        self.left_stick.setEnabled(enabled)
        self.right_stick.setEnabled(enabled)
        for btn in self.dpad_buttons.values():
            btn.setEnabled(enabled)

        if not enabled:
            self.left_stick.reset()
            self.right_stick.reset()
            self._keys_pressed.clear()
            self.dpad_status.setText("STANDBY")
            self.dpad_status.setStyleSheet("color: #78909c; font-family: Consolas; font-size: 8pt;")
            if was_enabled:
                self._emit("release_body_control", None)

    # ========================================================
    # SYNC FROM TELEMETRY
    # ========================================================

    def sync_targets(self, status):
        if not isinstance(status, dict):
            return
        alt = status.get("target_altitude")
        hdg = status.get("target_heading")
        if alt is not None:
            try:
                self.target_altitude = float(alt)
            except (TypeError, ValueError):
                pass
        if hdg is not None:
            try:
                self.target_heading = float(hdg)
            except (TypeError, ValueError):
                pass

    # ========================================================
    # TICK LOOP
    # ========================================================

    def _tick(self):
        if not self.isEnabled():
            return

        dt = self.TICK_MS / 1000.0

        left_x, left_y = self.left_stick.value()
        right_x, right_y = self.right_stick.value()

        left_x = self._apply_deadzone(left_x)
        left_y = self._apply_deadzone(left_y)
        right_x = self._apply_deadzone(right_x)
        right_y = self._apply_deadzone(right_y)

        yaw_rate = left_x * self.MAX_YAW_RATE
        climb_rate = left_y * self.MAX_CLIMB_RATE

        # 8-direction body-frame velocity
        forward_speed = right_y * self.MAX_SPEED
        lateral_speed = right_x * self.MAX_SPEED

        pitch_preview = right_y * self.MAX_TILT_ANGLE
        roll_preview = right_x * self.MAX_TILT_ANGLE

        self.left_readout.setText(
            f"yaw: {yaw_rate:+.1f} °/s   climb: {climb_rate:+.1f} m/s"
        )
        self.right_readout.setText(
            f"roll: {roll_preview:+.1f}°   pitch: {pitch_preview:+.1f}°"
        )

        if yaw_rate != 0.0:
            self.target_heading = (self.target_heading + yaw_rate * dt) % 360.0
            self._emit("heading", self.target_heading)

        if climb_rate != 0.0:
            self.target_altitude = max(0.0, self.target_altitude + climb_rate * dt)
            self._emit("altitude", self.target_altitude)

        # Emit 8-direction body velocity
        self._emit(
            "body_velocity",
            {
                "forward": forward_speed,
                "lateral": lateral_speed,
            },
        )

    def _apply_deadzone(self, value):
        if abs(value) < self.DEADZONE:
            return 0.0
        return value

    def _emit(self, command, value):
        if self.on_command is not None:
            self.on_command(command, value)
