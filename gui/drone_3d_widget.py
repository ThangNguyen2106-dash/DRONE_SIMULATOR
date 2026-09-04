from math import cos, sin, radians, sqrt, atan2, degrees

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class Drone3DWidget(QWidget):
    """Lightweight real-time 3D UAV attitude/position viewer.

    Coordinate system:
      X = East, Y = North, Z = Up.
    HOME is the fixed world origin (0, 0, 0). The aircraft position is
    calculated from lat/lon relative to HOME and altitude. Roll, pitch and yaw
    are applied to the aircraft mesh, so the UAV moves/rotates/tilts relative
    to the HOME marker instead of being a flat 2D icon.

    This is a software 3D renderer built with QPainter, so it needs only
    PySide6 and stays portable on Windows without an OpenGL dependency.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lat = 10.8231
        self.lon = 106.6297
        self.home_lat = self.lat
        self.home_lon = self.lon
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
        self._prop_angle = 0.0
        self._last_dt = 0.04

        self.setMinimumSize(320, 260)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(40)

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------
    def update_telemetry(self, status):
        if not isinstance(status, dict):
            return
        self.lat = self._num(status.get("lat"), self.lat)
        self.lon = self._num(status.get("lon"), self.lon)
        self.alt = max(0.0, self._num(status.get("alt"), self.alt))
        self.roll = self._num(status.get("roll"), self.roll)
        self.pitch = self._num(status.get("pitch"), self.pitch)
        self.yaw = self._num(status.get("yaw"), self.yaw)
        self.heading = self._num(status.get("heading"), self.heading)
        self.armed = bool(status.get("armed", self.armed))
        self.airborne = bool(status.get("airborne", self.alt > 0.08))
        self.mode = str(status.get("mode", status.get("flight_mode", self.mode)))
        self.speed = self._num(status.get("ground_speed"), self.speed)
        self.battery = self._num(status.get("battery"), self.battery)
        self.home_lat = self._num(status.get("home_lat"), self.home_lat)
        self.home_lon = self._num(status.get("home_lon"), self.home_lon)
        self.update()

    @staticmethod
    def _num(value, fallback):
        try:
            return float(value) if value is not None else float(fallback)
        except (TypeError, ValueError):
            return float(fallback)

    def _animate(self):
        if self.airborne and self.armed:
            self._prop_angle = (self._prop_angle + 42.0) % 360.0
        else:
            self._prop_angle = (self._prop_angle + 3.0) % 360.0
        self.update()

    # ------------------------------------------------------------------
    # World position: metres relative to HOME
    # ------------------------------------------------------------------
    def _relative_position(self):
        lat_scale = 111_320.0
        lon_scale = 111_320.0 * max(0.15, cos(radians(self.home_lat)))
        east = (self.lon - self.home_lon) * lon_scale
        north = (self.lat - self.home_lat) * lat_scale
        return east, north, self.alt

    # ------------------------------------------------------------------
    # 3D math / projection
    # ------------------------------------------------------------------
    @staticmethod
    def _rot(v, roll, pitch, yaw):
        """Body -> world rotation, aerospace convention."""
        x, y, z = v
        cr, sr = cos(radians(roll)), sin(radians(roll))
        cp, sp = cos(radians(pitch)), sin(radians(pitch))
        cy, sy = cos(radians(yaw)), sin(radians(yaw))

        # Roll around body X
        y, z = cr * y - sr * z, sr * y + cr * z
        # Pitch around body Y
        x, z = cp * x + sp * z, -sp * x + cp * z
        # Yaw around world Z
        x, y = cy * x - sy * y, sy * x + cy * y
        return x, y, z

    @staticmethod
    def _add(a, b):
        return a[0] + b[0], a[1] + b[1], a[2] + b[2]

    def _project(self, point, center, scale, camera_yaw=32.0, camera_pitch=54.0):
        x, y, z = point
        # Rotate world so North/East are shown in an oblique cockpit view.
        a = radians(camera_yaw)
        x, y = cos(a) * x - sin(a) * y, sin(a) * x + cos(a) * y
        # Tilt camera down while keeping the world Z axis intuitive:
        # positive Z (altitude) must move UP on screen, not down.
        # This is the key convention for the flight view:
        #   Z > 0  -> drone rises visually
        #   Z = 0  -> aircraft is on the HOME ground plane
        a = radians(camera_pitch)
        yy = cos(a) * y + sin(a) * z
        zz = sin(a) * y - cos(a) * z
        sx = center[0] + x * scale
        sy = center[1] - yy * scale
        depth = zz
        return QPointF(sx, sy), depth

    # ------------------------------------------------------------------
    # Mesh
    # ------------------------------------------------------------------
    def _mesh(self):
        """Detailed compact quadcopter mesh.

        Body nose is +Y.  The model is intentionally stylized like a modern
        enclosed-rotor UAV: dark arms/ducts, green center canopy and yellow
        propeller blades.  All geometry is still transformed in 3D by the
        attitude matrix below.
        """
        body = [
            (-0.78, -0.48, 0.02), (0.78, -0.48, 0.02),
            (0.68, 0.70, 0.02), (-0.68, 0.70, 0.02),
            (-0.60, -0.38, 0.34), (0.60, -0.38, 0.34),
            (0.50, 0.52, 0.27), (-0.50, 0.52, 0.27),
        ]
        faces = [
            ([0, 1, 2, 3], "body_bottom"),
            ([4, 7, 6, 5], "body_top"),
            ([0, 4, 5, 1], "body_side"),
            ([1, 5, 6, 2], "body_side"),
            ([2, 6, 7, 3], "body_front"),
            ([3, 7, 4, 0], "body_side"),
        ]

        arms, motors, rotors = [], [], []
        for x in (-1, 1):
            for y in (-1, 1):
                mx, my = 1.42 * x, 1.08 * y
                # Wide, tapered-looking arm prism.
                ax, ay = 0.42 * x, 0.32 * y
                arm = [
                    (ax - .11, ay - .09, .10),
                    (mx + .11*x, my + .09*y, .10),
                    (mx + .11*x, my + .09*y, .25),
                    (ax - .11, ay - .09, .25),
                ]
                arms.append(arm)
                motors.append((mx, my, 0.27))
                rotors.append((mx, my, 0.34))

        gear = [
            ((-0.52, -0.30, -0.38), (-0.52, 0.42, -0.38)),
            ((0.52, -0.30, -0.38), (0.52, 0.42, -0.38)),
            ((-0.52, -0.30, -0.03), (-0.52, -0.30, -0.38)),
            ((0.52, -0.30, -0.03), (0.52, -0.30, -0.38)),
        ]
        return body, faces, arms, motors, rotors, gear

    def _visual_yaw(self):
        """Convert compass heading to the math angle used by Rz.

        World axes are X=East, Y=North, Z=Up and the model nose is +Y.
        Heading is compass clockwise from North, so a clockwise heading is
        represented by a negative mathematical Z rotation.  This guarantees
        a full 0..360 degree heading rotation around the Z axis.
        """
        return -float(self.heading) % 360.0

    def _draw_mesh(self, p, center, scale, pos):
        body, faces, arms, motors, rotors, gear = self._mesh()
        roll = max(-65.0, min(65.0, self.roll))
        pitch = max(-55.0, min(55.0, self.pitch))
        # IMPORTANT: visual heading is a pure world-Z rotation.
        yaw = self._visual_yaw()

        def world(v):
            return self._add(pos, self._rot(v, roll, pitch, yaw))

        render_faces = []
        for ids, kind in faces:
            pts3 = [world(body[i]) for i in ids]
            proj = [self._project(q, center, scale) for q in pts3]
            depth = sum(q[1] for q in proj) / len(proj)
            render_faces.append((depth, [q[0] for q in proj], kind))

        for arm in arms:
            pts3 = [world(v) for v in arm]
            proj = [self._project(q, center, scale) for q in pts3]
            depth = sum(q[1] for q in proj) / len(proj)
            render_faces.append((depth, [q[0] for q in proj], "arm"))

        render_faces.sort(key=lambda item: item[0])
        for _, pts, kind in render_faces:
            poly = QPolygonF(pts)
            if kind == "body_top":
                fill, edge = QColor("#39a94b"), QColor("#9af36e")
            elif kind == "body_front":
                fill, edge = QColor("#23803a"), QColor("#58cf62")
            elif kind == "body_side":
                fill, edge = QColor("#155a2c"), QColor("#347c42")
            elif kind == "arm":
                fill, edge = QColor("#1c2329"), QColor("#56616a")
            else:
                fill, edge = QColor("#11171c"), QColor("#35414a")
            p.setBrush(fill)
            p.setPen(QPen(edge, max(1, int(scale * 0.8))))
            p.drawPolygon(poly)

        # Canopy highlight, transformed with the body.
        canopy = [world(v) for v in [(-0.42, -0.28, 0.35), (0.42, -0.28, 0.35),
                                     (0.34, 0.42, 0.30), (-0.34, 0.42, 0.30)]]
        canopy2 = [self._project(q, center, scale)[0] for q in canopy]
        p.setBrush(QColor("#52d85d"))
        p.setPen(QPen(QColor("#a8ff72"), max(1, int(scale * .6))))
        p.drawPolygon(QPolygonF(canopy2))

        # Four enclosed rotor guards + motors + spinning blades.
        for idx, motor in enumerate(motors):
            m3 = world(motor)
            q, _ = self._project(m3, center, scale)
            ring_r = 0.43 * scale
            ring_y = 0.48 * ring_r
            p.setBrush(QColor(10, 15, 18, 185))
            p.setPen(QPen(QColor(50, 59, 65, 245), max(2, int(scale * 1.8))))
            p.drawEllipse(q, ring_r, ring_y)
            p.setPen(QPen(QColor(130, 142, 148, 155), max(1, int(scale * .65))))
            p.drawEllipse(q, ring_r * .84, ring_y * .84)

            p.setBrush(QColor("#151a1e"))
            p.setPen(QPen(QColor("#59656d"), max(1, int(scale * .55))))
            p.drawEllipse(q, 0.15 * scale, 0.15 * scale)

            # Rotor plane follows the local body orientation.  The projected
            # blade pair is deliberately thin, with yellow tips like the
            # reference UAV.
            r3 = world(rotors[idx])
            rq, _ = self._project(r3, center, scale)
            angle = radians(self._prop_angle * (1 if idx % 2 == 0 else -1))
            dx = cos(angle) * ring_r * .86
            dy = sin(angle) * ring_r * .30
            p.setPen(QPen(QColor("#d7e0e3",), max(2, int(scale * 1.2))))
            p.drawLine(QPointF(rq.x()-dx, rq.y()-dy), QPointF(rq.x()+dx, rq.y()+dy))
            p.setPen(QPen(QColor("#f2d84b",), max(2, int(scale * 1.6))))
            p.drawLine(QPointF(rq.x()-dx*.88, rq.y()-dy*.88), QPointF(rq.x()-dx*.58, rq.y()-dy*.58))
            p.drawLine(QPointF(rq.x()+dx*.58, rq.y()+dy*.58), QPointF(rq.x()+dx*.88, rq.y()+dy*.88))

        p.setPen(QPen(QColor("#303a42"), max(2, int(scale * 1.4))))
        for a, b in gear:
            qa = self._project(world(a), center, scale)[0]
            qb = self._project(world(b), center, scale)[0]
            p.drawLine(qa, qb)

        # Bright nose chevron makes heading direction unmistakable.
        nose_a = self._project(world((0, 0.42, 0.33)), center, scale)[0]
        nose_b = self._project(world((0, 1.10, 0.33)), center, scale)[0]
        p.setPen(QPen(QColor("#ffe35a"), max(2, int(scale * 2.0))))
        p.drawLine(nose_a, nose_b)
        p.drawEllipse(nose_b, max(2, scale*.10), max(2, scale*.10))

    # ------------------------------------------------------------------
    # Ground / HOME
    # ------------------------------------------------------------------
    def _draw_ground(self, p, center, scale, w, h):
        floor_y = int(h * 0.50)
        p.fillRect(0, floor_y, w, h - floor_y, QColor("#08111a"))

        # Perspective grid centered on HOME.
        p.setPen(QPen(QColor(48, 67, 84, 145), 1))
        grid = 8
        extent = 35.0
        for i in range(-grid, grid + 1):
            x = i * extent / grid
            a = self._project((x, -extent, 0), center, scale)[0]
            b = self._project((x, extent, 0), center, scale)[0]
            p.drawLine(a, b)
            y = i * extent / grid
            a = self._project((-extent, y, 0), center, scale)[0]
            b = self._project((extent, y, 0), center, scale)[0]
            p.drawLine(a, b)

        home = self._project((0, 0, 0), center, scale)[0]
        r = max(34.0, 2.8 * scale)
        # HOME rings use a screen-space ellipse to remain readable.
        p.setPen(QPen(QColor("#4dd7ff"), max(2, int(scale * 1.2))))
        p.setBrush(QColor(45, 190, 230, 24))
        p.drawEllipse(home, r, r * 0.40)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(home, r * 0.62, r * 0.25)
        p.setPen(QPen(QColor(90, 210, 240, 120), 1))
        p.drawLine(QPointF(home.x() - r * 1.3, home.y()), QPointF(home.x() + r * 1.3, home.y()))
        p.drawLine(QPointF(home.x(), home.y() - r * .55), QPointF(home.x(), home.y() + r * .55))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#54d9ff"))
        p.drawEllipse(home, 5, 5)
        p.setPen(QColor("#c8f4ff"))
        p.setFont(QFont("Segoe UI", max(8, int(9 * scale)), QFont.Weight.DemiBold))
        p.drawText(int(home.x() + r + 8), int(home.y() + 4), "HOME")

        # North arrow.
        p.setPen(QPen(QColor("#9eb1c1"), 1))
        p.drawLine(w - 40, 47, w - 40, 23)
        p.drawLine(w - 45, 30, w - 40, 23)
        p.drawLine(w - 35, 30, w - 40, 23)
        p.drawText(w - 49, 17, "N")

    # ------------------------------------------------------------------
    # UI overlay
    # ------------------------------------------------------------------
    def _draw_overlay(self, p, w, h, scale, distance):
        airborne = self.airborne and self.alt > 0.08
        state = "FLYING" if airborne else ("ARMED / ON GROUND" if self.armed else "LANDED")
        state_color = QColor("#35d07a") if airborne else (QColor("#f0b84b") if self.armed else QColor("#7f91a5"))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(11, 22, 34, 230))
        p.drawRoundedRect(16, 14, min(235, w - 32), 34, 9, 9)
        p.setBrush(state_color)
        p.drawEllipse(28, 25, 12, 12)
        p.setPen(QColor("#edf5fb"))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        p.drawText(48, 37, state)

        p.setPen(QColor("#9bb0c3"))
        p.setFont(QFont("Consolas", 8))
        p.drawText(16, 68, f"MODE {self.mode.upper()}")
        p.drawText(16, 84, f"ALT  {self.alt:6.1f} m")
        p.drawText(16, 100, f"HOME {distance:6.1f} m")

        values = [("ROLL", self.roll, "°"), ("PITCH", self.pitch, "°"),
                  ("HDG / Z", self.heading, "°"), ("SPD", self.speed, " m/s")]
        box_w = max(72, int((w - 40) / 4))
        y = h - 64
        for i, (label, value, suffix) in enumerate(values):
            x = 8 + i * box_w
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(13, 24, 38, 230))
            p.drawRoundedRect(x, y, box_w - 5, 48, 7, 7)
            p.setPen(QColor("#8196ab"))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            p.drawText(x + 8, y + 15, label)
            p.setPen(QColor("#edf5fb"))
            p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            p.drawText(x + 8, y + 35, f"{value:5.1f}{suffix}")

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            w, h = self.width(), self.height()
            p.fillRect(self.rect(), QColor("#0b1420"))

            # Sky gradient bands.
            sky_h = int(h * 0.52)
            for y in range(sky_h):
                t = y / max(1, sky_h)
                c = QColor(int(12 + 10 * t), int(23 + 11 * t), int(39 + 15 * t))
                p.setPen(c)
                p.drawLine(0, y, w, y)

            # Adaptive camera: fit HOME and the aircraft together so the
            # whole flight volume remains visible even at high altitude or
            # when the aircraft is far from HOME. The viewport uses almost
            # all available space; overlays sit on top of it.
            east, north, altitude = self._relative_position()
            pos = (east, north, altitude)

            # Choose a camera target halfway between HOME and the aircraft.
            # This keeps both references visible instead of letting a high
            # altitude aircraft leave the top of the viewport.
            target_x = east * 0.50
            target_y = north * 0.50
            target_z = altitude * 0.42

            # Larger value = wider world visible. The scale is derived from
            # the largest span of the current flight volume and padded so the
            # drone and HOME never touch the edges.
            horizontal_span = max(35.0, abs(east) * 2.0 + 20.0, abs(north) * 2.0 + 20.0)
            vertical_span = max(25.0, altitude * 1.35 + 16.0)
            world_span = max(horizontal_span, vertical_span)
            scene_w = max(280.0, w - 24.0)
            scene_h = max(220.0, h - 92.0)
            scale = max(1.35, min(scene_w / world_span, scene_h / world_span))
            # Keep a useful minimum model size while still allowing very high
            # altitude missions to zoom out automatically.
            scale = min(scale, max(1.6, min(w, h) / 25.0))

            # Center the camera around the flight volume.
            center = (w * 0.50 - target_x * scale, h * 0.58 + target_y * scale + target_z * scale)

            self._draw_ground(p, center, scale, w, h)
            home_screen = self._project((0, 0, 0), center, scale)[0]
            drone_screen = self._project(pos, center, scale)[0]

            # HOME -> aircraft tether showing actual 3D relative position.
            if altitude > 0.05 or abs(east) > 0.2 or abs(north) > 0.2:
                p.setPen(QPen(QColor(83, 215, 255, 125), 1, Qt.PenStyle.DashLine))
                p.drawLine(drone_screen, home_screen)

            # Ground shadow projected at aircraft's XY position.
            ground_screen = self._project((east, north, 0), center, scale)[0]
            shadow = max(5.0, 18.0 - min(altitude, 18.0) * 0.6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 95))
            p.drawEllipse(ground_screen, shadow * 1.5, shadow * 0.45)

            self._draw_mesh(p, center, scale, pos)

            distance = sqrt(east * east + north * north + altitude * altitude)
            self._draw_overlay(p, w, h, scale / 2.5, distance)
        finally:
            p.end()
