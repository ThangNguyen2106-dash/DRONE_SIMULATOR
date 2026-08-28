import math

from PySide6.QtCore import Qt, QTimer, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QWidget,
)


# ============================================================
# VIRTUAL JOYSTICK WIDGET
# ============================================================

class JoystickWidget(QWidget):
    """
    On-screen virtual joystick.

    Drag the knob with the mouse; it springs back to the
    center on release. Emits normalized axis values in
    [-1.0, 1.0], with +y meaning "up" (screen-up, not
    Qt's down-positive convention).
    """

    moved = Signal(float, float)

    def __init__(self, parent=None, diameter=140):

        super().__init__(parent)

        self._diameter = diameter

        self._knob_radius = 16

        self._max_travel = (
            diameter / 2 - self._knob_radius - 4
        )

        self._x = 0.0
        self._y = 0.0

        self._dragging = False

        self.setFixedSize(diameter, diameter)

        self.setCursor(Qt.OpenHandCursor)

    # --------------------------------------------------------

    def value(self):
        return self._x, self._y

    # --------------------------------------------------------

    def _center(self):
        return QPointF(
            self.width() / 2,
            self.height() / 2,
        )

    # --------------------------------------------------------

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

    # --------------------------------------------------------

    def reset(self):

        self._x = 0.0
        self._y = 0.0

        self.update()

        self.moved.emit(0.0, 0.0)

    # --------------------------------------------------------
    # MOUSE
    # --------------------------------------------------------

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

    def leaveEvent(self, event):

        if self._dragging:
            return

        super().leaveEvent(event)

    # --------------------------------------------------------
    # PAINT
    # --------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(QPainter.Antialiasing)

        center = self._center()

        # ----------------------------------------------------
        # Base circle.
        # ----------------------------------------------------

        painter.setPen(QPen(QColor(90, 90, 90), 2))
        painter.setBrush(QBrush(QColor(40, 40, 40)))

        painter.drawEllipse(
            center,
            self._diameter / 2 - 2,
            self._diameter / 2 - 2,
        )

        # ----------------------------------------------------
        # Crosshair.
        # ----------------------------------------------------

        painter.setPen(QPen(QColor(70, 70, 70), 1))

        painter.drawLine(
            2, int(center.y()),
            self.width() - 2, int(center.y()),
        )

        painter.drawLine(
            int(center.x()), 2,
            int(center.x()), self.height() - 2,
        )

        # ----------------------------------------------------
        # Knob.
        # ----------------------------------------------------

        knob_pos = QPointF(
            center.x() + self._x * self._max_travel,
            center.y() - self._y * self._max_travel,
        )

        painter.setPen(QPen(QColor(30, 120, 200), 2))
        painter.setBrush(QBrush(QColor(50, 160, 240)))

        painter.drawEllipse(
            knob_pos,
            self._knob_radius,
            self._knob_radius,
        )


# ============================================================
# JOYSTICK PANEL
# ============================================================

class JoystickPanel(QGroupBox):
    """
    Two virtual joysticks for flying the drone in FREE mode:

      LEFT  stick  -> X: yaw rate      Y: climb / descend rate
      RIGHT stick  -> Y: forward speed (X unused)

    Commands are forwarded to plain callback attributes so
    this widget stays decoupled from SimulationWorker, in
    line with ManualControlPanel / FailurePanel.
    """

    MAX_YAW_RATE = 60.0
    MAX_CLIMB_RATE = 3.0
    MAX_SPEED = 15.0

    TICK_MS = 50

    DEADZONE = 0.05

    def __init__(self, parent=None):

        super().__init__("JOYSTICK CONTROL", parent)

        self.on_command = None

        self.target_altitude = 0.0
        self.target_heading = 0.0

        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.set_enabled(False)

    # ========================================================
    # UI
    # ========================================================

    def _setup_ui(self):

        layout = QHBoxLayout()

        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(30)

        # ----------------------------------------------------
        # LEFT: YAW / ALTITUDE
        # ----------------------------------------------------

        left_box = QVBoxLayout()

        left_label = QLabel("YAW / ALTITUDE")
        left_label.setAlignment(Qt.AlignCenter)

        self.left_stick = JoystickWidget()

        left_box.addWidget(left_label)
        left_box.addWidget(
            self.left_stick, 0, Qt.AlignCenter
        )

        self.left_readout = QLabel("yaw: 0.0 °/s   climb: 0.0 m/s")
        self.left_readout.setAlignment(Qt.AlignCenter)

        left_box.addWidget(self.left_readout)

        layout.addLayout(left_box)

        # ----------------------------------------------------
        # RIGHT: SPEED
        # ----------------------------------------------------

        right_box = QVBoxLayout()

        right_label = QLabel("SPEED")
        right_label.setAlignment(Qt.AlignCenter)

        self.right_stick = JoystickWidget()

        right_box.addWidget(right_label)
        right_box.addWidget(
            self.right_stick, 0, Qt.AlignCenter
        )

        self.right_readout = QLabel("speed: 0.0 m/s")
        self.right_readout.setAlignment(Qt.AlignCenter)

        right_box.addWidget(self.right_readout)

        layout.addLayout(right_box)

        self.setLayout(layout)

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(self, enabled):

        self.left_stick.setEnabled(enabled)
        self.right_stick.setEnabled(enabled)

        if not enabled:

            self.left_stick.reset()
            self.right_stick.reset()

    # ========================================================
    # SYNC FROM TELEMETRY
    # ========================================================

    def sync_targets(self, status):
        """
        Keep the internally tracked altitude / heading targets
        aligned with the simulator so the joystick doesn't
        jump when picked back up after being idle.
        """

        if not isinstance(status, dict):
            return

        altitude = status.get("target_altitude")
        heading = status.get("target_heading")

        if altitude is not None:

            try:
                self.target_altitude = float(altitude)
            except (TypeError, ValueError):
                pass

        if heading is not None:

            try:
                self.target_heading = float(heading)
            except (TypeError, ValueError):
                pass

    # ========================================================
    # TICK
    # ========================================================

    def _tick(self):

        if not self.isEnabled():
            return

        dt = self.TICK_MS / 1000.0

        left_x, left_y = self.left_stick.value()
        right_x, right_y = self.right_stick.value()

        left_x = self._apply_deadzone(left_x)
        left_y = self._apply_deadzone(left_y)
        right_y = self._apply_deadzone(right_y)

        yaw_rate = left_x * self.MAX_YAW_RATE
        climb_rate = left_y * self.MAX_CLIMB_RATE

        speed = max(
            0.0,
            right_y * self.MAX_SPEED,
        )

        self.left_readout.setText(
            f"yaw: {yaw_rate:+.1f} °/s   "
            f"climb: {climb_rate:+.1f} m/s"
        )

        self.right_readout.setText(
            f"speed: {speed:.1f} m/s"
        )

        if yaw_rate == 0.0 and climb_rate == 0.0 and speed == 0.0:
            return

        if yaw_rate != 0.0:

            self.target_heading = (
                self.target_heading + yaw_rate * dt
            ) % 360.0

            self._emit("heading", self.target_heading)

        if climb_rate != 0.0:

            self.target_altitude = max(
                0.0,
                self.target_altitude + climb_rate * dt,
            )

            self._emit("altitude", self.target_altitude)

        self._emit("speed", speed)

    # --------------------------------------------------------

    def _apply_deadzone(self, value):

        if abs(value) < self.DEADZONE:
            return 0.0

        return value

    # --------------------------------------------------------

    def _emit(self, command, value):

        if self.on_command is not None:
            self.on_command(command, value)
