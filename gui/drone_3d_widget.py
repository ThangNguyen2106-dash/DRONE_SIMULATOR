from math import cos, radians, sin
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTransform
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget


class Drone3DWidget(QWidget):
    """Visual attitude/altitude viewer for the simulator.

    The aircraft is a clean UAV illustration rather than a geometric 3D
    mesh. HOME stays fixed on the ground while altitude, yaw, roll and pitch
    transform the aircraft above it. This keeps the view intuitive and light.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alt = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.heading = 0.0
        self.armed = False
        self.airborne = False
        self.mode = "STANDBY"
        self.speed = 0.0
        self.battery = 100.0
        self._spin = 0.0

        asset = Path(__file__).resolve().parent.parent / "assets" / "drone_uav.svg"
        self._renderer = QSvgRenderer(str(asset))

        self.setMinimumSize(320, 260)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(40)

    def update_telemetry(self, status):
        if not isinstance(status, dict):
            return
        self.alt = float(status.get("alt", self.alt) or 0)
        self.roll = float(status.get("roll", self.roll) or 0)
        self.pitch = float(status.get("pitch", self.pitch) or 0)
        self.yaw = float(status.get("yaw", self.yaw) or 0)
        self.heading = float(status.get("heading", self.heading) or 0)
        self.armed = bool(status.get("armed", self.armed))
        self.airborne = bool(status.get("airborne", self.alt > 0.08))
        self.mode = str(status.get("mode", status.get("flight_mode", self.mode)))
        self.speed = float(status.get("ground_speed", self.speed) or 0)
        self.battery = float(status.get("battery", self.battery) or 0)
        self.update()

    def _animate(self):
        if self.airborne and self.armed:
            self._spin = (self._spin + 20.0) % 360.0
        else:
            self._spin = (self._spin + 2.0) % 360.0
        self.update()

    def _draw_ground(self, p, cx, home_y, w, h, scale):
        # Soft perspective floor.
        floor_top = max(int(h * 0.50), int(home_y - 40 * scale))
        p.fillRect(0, floor_top, w, h - floor_top, QColor("#0a111b"))

        p.setPen(QPen(QColor(39, 57, 76, 150), 1))
        for i in range(-9, 10):
            x = cx + i * 42 * scale
            p.drawLine(QPointF(x, floor_top), QPointF(cx + i * 86 * scale, h))
        for i in range(0, 7):
            y = floor_top + (i * i) * max(7, 5 * scale)
            p.drawLine(QPointF(0, y), QPointF(w, y))

        # HOME target.
        r = max(34, 54 * scale)
        p.setPen(QPen(QColor("#55d6ff"), max(2, int(2 * scale))))
        p.setBrush(QColor(30, 150, 190, 24))
        p.drawEllipse(QPointF(cx, home_y), r, r * 0.42)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, home_y), r * 0.62, r * 0.26)
        p.setPen(QPen(QColor(85, 214, 255, 130), 1))
        p.drawLine(QPointF(cx - r * 1.25, home_y), QPointF(cx + r * 1.25, home_y))
        p.drawLine(QPointF(cx, home_y - r * 0.55), QPointF(cx, home_y + r * 0.55))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#55d6ff"))
        p.drawEllipse(QPointF(cx, home_y), 5, 5)
        p.setPen(QColor("#bfeeff"))
        p.setFont(QFont("Segoe UI", max(8, int(9 * scale)), QFont.Weight.DemiBold))
        p.drawText(int(cx + r + 8), int(home_y + 4), "HOME")

        # North indicator.
        p.setPen(QPen(QColor("#8296aa"), 1))
        p.drawLine(QPointF(w - 38, 48), QPointF(w - 38, 24))
        p.drawLine(QPointF(w - 43, 31), QPointF(w - 38, 24))
        p.drawLine(QPointF(w - 33, 31), QPointF(w - 38, 24))
        p.setPen(QColor("#a8bacb"))
        p.drawText(w - 47, 18, "N")

    def _draw_drone(self, p, cx, home_y, scale):
        # Altitude is represented by lift above HOME, capped for readability.
        lift = min(max(self.alt, 0.0), 120.0) * 1.9 * scale
        lift = max(0.0, lift)
        drone_x = cx
        drone_y = home_y - lift

        # Vertical altitude line.
        if self.alt > 0.05:
            p.setPen(QPen(QColor(90, 213, 255, 120), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(drone_x, drone_y + 32 * scale), QPointF(cx, home_y - 4))

        # Dynamic shadow under aircraft.
        shadow_scale = max(0.32, 1.0 - min(self.alt, 80.0) / 100.0)
        shadow_w = 60 * scale * shadow_scale
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 85))
        p.drawEllipse(QPointF(cx, home_y + 8), shadow_w, shadow_w * 0.24)

        # Render the drone into a transformed coordinate system.
        base_w = 210 * scale
        base_h = base_w * 520.0 / 800.0

        # Pitch: positive pitch visually raises the nose and compresses the
        # vertical depth. Roll: lean left/right. Yaw: rotate heading.
        pitch = max(-35.0, min(35.0, self.pitch))
        roll = max(-45.0, min(45.0, self.roll))
        yaw = self.yaw

        p.save()
        p.translate(drone_x, drone_y)
        p.rotate(yaw)
        p.rotate(roll)
        pitch_factor = 1.0 - abs(pitch) / 70.0
        p.scale(1.0, max(0.55, pitch_factor))
        p.translate(-base_w / 2, -base_h / 2)
        self._renderer.render(p, 0, 0, int(base_w), int(base_h))
        p.restore()

        # Small attitude vectors around the aircraft.
        p.setPen(QPen(QColor("#ffb84a"), max(1, int(2 * scale))))
        vx = 34 * scale * cos(radians(yaw))
        vy = 34 * scale * sin(radians(yaw))
        p.drawLine(QPointF(drone_x, drone_y), QPointF(drone_x + vx, drone_y + vy))

    def _draw_overlay(self, p, w, h, scale):
        airborne = self.airborne and self.alt > 0.08
        state = "FLYING" if airborne else ("ARMED / ON GROUND" if self.armed else "LANDED")
        state_color = QColor("#35d07a") if airborne else (QColor("#f0b84b") if self.armed else QColor("#7f91a5"))

        # Status badge.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(12, 22, 35, 225))
        p.drawRoundedRect(16, 14, min(220, w - 32), 34, 9, 9)
        p.setBrush(state_color)
        p.drawEllipse(28, 25, 12, 12)
        p.setPen(QColor("#e8f1f8"))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(48, 37, state)

        # Attitude cards.
        values = [
            ("ROLL", self.roll),
            ("PITCH", self.pitch),
            ("YAW", self.yaw),
            ("ALT", self.alt),
        ]
        box_w = max(70, int((w - 40) / 4))
        y = h - 64
        for i, (label, value) in enumerate(values):
            x = 8 + i * box_w
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(13, 24, 38, 225))
            p.drawRoundedRect(x, y, box_w - 5, 48, 7, 7)
            p.setPen(QColor("#8196ab"))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.drawText(x + 8, y + 15, label)
            p.setPen(QColor("#edf5fb"))
            p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            suffix = " m" if label == "ALT" else "°"
            p.drawText(x + 8, y + 35, f"{value:5.1f}{suffix}")

        # Mode / speed in the upper right.
        p.setPen(QColor("#91a7bb"))
        p.setFont(QFont("Consolas", 9))
        p.drawText(16, 68, f"MODE  {self.mode.upper()}")
        p.drawText(16, 84, f"SPD   {self.speed:5.1f} m/s")
        p.drawText(16, 100, f"HDG   {self.heading:5.1f}°")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#0b1220"))

        # Subtle sky gradient using horizontal bands (keeps it dependency-free).
        for y in range(int(h * 0.52)):
            t = y / max(1, h * 0.52)
            c = QColor(int(14 + 7 * t), int(25 + 9 * t), int(41 + 12 * t))
            p.setPen(c)
            p.drawLine(0, y, w, y)

        scale = max(0.72, min(w, h) / 430.0)
        cx = w * 0.5
        home_y = h * 0.67

        self._draw_ground(p, cx, home_y, w, h, scale)
        self._draw_drone(p, cx, home_y, scale)
        self._draw_overlay(p, w, h, scale)
        p.end()
