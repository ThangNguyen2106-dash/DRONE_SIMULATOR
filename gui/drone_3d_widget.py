from math import cos, sin, radians, sqrt, atan2, degrees
import time

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget


class Drone3DWidget(QWidget):
    """Lightweight real-time 3D UAV attitude/position viewer with enhanced
    smooth rendering, dynamic 3D lighting, and high-fidelity drone mesh.

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

        # Raw telemetry targets
        self._target_lat = 10.665606
        self._target_lon = 106.671538
        self.home_lat = 10.665606
        self.home_lon = 106.671538
        self._target_alt = 0.0
        self._target_roll = 0.0
        self._target_pitch = 0.0
        self._target_yaw = 0.0
        self._target_heading = 0.0
        self._target_speed = 0.0
        self.battery = 100.0
        self.armed = False
        self.airborne = False
        self.mode = "STANDBY"

        # Smooth interpolated display states
        self.lat = self._target_lat
        self.lon = self._target_lon
        self.alt = self._target_alt
        self.roll = self._target_roll
        self.pitch = self._target_pitch
        self.yaw = self._target_yaw
        self.heading = self._target_heading
        self.speed = self._target_speed

        # Animation states
        self._prop_angle = 0.0
        self._prop_speed = 0.0
        self._last_time = time.perf_counter()

        # Directional sun vector for dynamic 3D shading
        self._light_dir = self._normalize_vec((0.45, -0.65, 0.75))

        self.setMinimumSize(320, 260)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # 60 FPS high-refresh animation loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(16)

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------
    def update_telemetry(self, status):
        if not isinstance(status, dict):
            return
        self._target_lat = self._num(status.get("lat"), self._target_lat)
        self._target_lon = self._num(status.get("lon"), self._target_lon)
        self._target_alt = max(0.0, self._num(status.get("alt"), self._target_alt))
        self._target_roll = self._num(status.get("roll"), self._target_roll)
        self._target_pitch = self._num(status.get("pitch"), self._target_pitch)
        self._target_yaw = self._num(status.get("yaw"), self._target_yaw)
        self._target_heading = self._num(status.get("heading"), self._target_heading)
        self.armed = bool(status.get("armed", self.armed))
        self.airborne = bool(status.get("airborne", self._target_alt > 0.08))
        self.mode = str(status.get("mode", status.get("flight_mode", self.mode)))
        self._target_speed = self._num(status.get("ground_speed"), self._target_speed)
        self.battery = self._num(status.get("battery"), self.battery)
        self.home_lat = self._num(status.get("home_lat"), self.home_lat)
        self.home_lon = self._num(status.get("home_lon"), self.home_lon)

    @staticmethod
    def _num(value, fallback):
        try:
            return float(value) if value is not None else float(fallback)
        except (TypeError, ValueError):
            return float(fallback)

    @staticmethod
    def _diff_angle(curr, target):
        d = (target - curr) % 360.0
        if d > 180.0:
            d -= 360.0
        return d

    def _animate(self):
        now = time.perf_counter()
        dt = max(0.001, min(0.08, now - self._last_time))
        self._last_time = now

        # Smooth exponential interpolation (eliminates telemetry jitter)
        lerp_pos = 1.0 - (0.0005 ** dt)
        lerp_rot = 1.0 - (0.0001 ** dt)

        self.lat += (self._target_lat - self.lat) * lerp_pos
        self.lon += (self._target_lon - self.lon) * lerp_pos
        self.alt += (self._target_alt - self.alt) * lerp_pos
        self.speed += (self._target_speed - self.speed) * lerp_pos

        self.roll += (self._target_roll - self.roll) * lerp_rot
        self.pitch += (self._target_pitch - self.pitch) * lerp_rot
        self.yaw += self._diff_angle(self.yaw, self._target_yaw) * lerp_rot
        self.heading += self._diff_angle(self.heading, self._target_heading) * lerp_rot

        # Propeller RPM spool-up/spool-down with realistic inertia
        target_rpm = 1.0 if (self.airborne and self.armed) else (0.25 if self.armed else 0.0)
        self._prop_speed += (target_rpm - self._prop_speed) * (1.0 - (0.02 ** dt))

        # Advance prop rotation angle
        prop_rate = self._prop_speed * 1350.0 + (35.0 if self.armed else 8.0)
        self._prop_angle = (self._prop_angle + prop_rate * dt) % 360.0

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
    def _normalize_vec(v):
        x, y, z = v
        length = sqrt(x * x + y * y + z * z)
        if length < 1e-6:
            return 0.0, 0.0, 1.0
        return x / length, y / length, z / length

    @staticmethod
    def _cross_product(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    @staticmethod
    def _dot_product(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _rot(v, roll, pitch, yaw):
        """Body -> world rotation, aerospace convention.
        Body coordinate axes: +X = Right, +Y = Forward (Nose), +Z = Up.
        """
        x, y, z = v
        cr, sr = cos(radians(roll)), sin(radians(roll))
        cp, sp = cos(radians(pitch)), sin(radians(pitch))
        cy, sy = cos(radians(yaw)), sin(radians(yaw))

        # Pitch around body X (transverse axis): pitch < 0 tilts nose (+Y) down towards -Z
        y, z = cp * y - sp * z, sp * y + cp * z

        # Roll around body Y (longitudinal axis): roll > 0 tilts right wing (+X) down towards -Z
        x, z = cr * x + sr * z, -sr * x + cr * z

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
    # High-Detail 3D Mesh
    # ------------------------------------------------------------------
    def _mesh(self):
        """Refined aerodynamic UAV mesh with fuselage, gimbal camera,
        carbon fiber arms, brushless motors, and landing skids.
        """
        # Central Fuselage vertices (Nose is +Y, Right is +X, Up is +Z)
        v = [
            # Bottom hull (0..7)
            (-0.48, -0.65, 0.02), (0.48, -0.65, 0.02),
            (0.54, -0.10, 0.01), (-0.54, -0.10, 0.01),
            (0.48, 0.45, 0.02), (-0.48, 0.45, 0.02),
            (0.28, 0.76, 0.04), (-0.28, 0.76, 0.04),

            # Mid waist line (8..15)
            (-0.54, -0.68, 0.18), (0.54, -0.68, 0.18),
            (0.62, -0.10, 0.18), (-0.62, -0.10, 0.18),
            (0.56, 0.48, 0.19), (-0.56, 0.48, 0.19),
            (0.32, 0.82, 0.17), (-0.32, 0.82, 0.17),

            # Top deck (16..23)
            (-0.40, -0.55, 0.35), (0.40, -0.55, 0.35),
            (0.46, -0.10, 0.36), (-0.46, -0.10, 0.36),
            (0.42, 0.40, 0.34), (-0.42, 0.40, 0.34),
            (0.24, 0.68, 0.28), (-0.24, 0.68, 0.28),

            # Canopy ridge (24..27)
            (-0.20, -0.40, 0.40), (0.20, -0.40, 0.40),
            (0.18, 0.28, 0.39), (-0.18, 0.28, 0.39),
        ]

        # Faces with base color and lighting classification
        faces = [
            # Lower belly
            ([0, 1, 2, 3], "bottom", QColor("#141a20")),
            ([3, 2, 4, 5], "bottom", QColor("#141a20")),
            ([5, 4, 6, 7], "bottom", QColor("#141a20")),

            # Lower side chamfers
            ([0, 8, 9, 1], "side", QColor("#1c232a")),
            ([1, 9, 10, 2], "side", QColor("#202830")),
            ([2, 10, 12, 4], "side", QColor("#222b34")),
            ([4, 12, 14, 6], "side", QColor("#25303a")),
            ([6, 14, 15, 7], "front", QColor("#2b3742")),
            ([7, 15, 13, 5], "side", QColor("#25303a")),
            ([5, 13, 11, 3], "side", QColor("#222b34")),
            ([3, 11, 8, 0], "side", QColor("#202830")),

            # Upper side chamfers
            ([8, 16, 17, 9], "top_side", QColor("#28343f")),
            ([9, 17, 18, 10], "top_side", QColor("#2f3c49")),
            ([10, 18, 20, 12], "top_side", QColor("#334250")),
            ([12, 20, 22, 14], "top_side", QColor("#384858")),
            ([14, 22, 23, 15], "front", QColor("#405364")),
            ([15, 23, 21, 13], "top_side", QColor("#384858")),
            ([13, 21, 19, 11], "top_side", QColor("#334250")),
            ([11, 19, 16, 8], "top_side", QColor("#2f3c49")),

            # Canopy top
            ([16, 24, 25, 17], "top", QColor("#334454")),
            ([16, 19, 27, 24], "top", QColor("#384a5c")),
            ([17, 25, 26, 18], "top", QColor("#384a5c")),
            ([19, 21, 27, 27], "top", QColor("#3e5266")),
            ([18, 26, 20, 20], "top", QColor("#3e5266")),
            ([24, 27, 26, 25], "canopy_accent", QColor("#ff6b22")),  # Canopy accent
            ([21, 23, 22, 20], "top", QColor("#44596e")),
        ]

        # 4 Carbon fiber arms
        arms = []
        motors = []
        rotors = []
        nav_leds = []

        arm_params = [
            (1.42, 1.08, QColor("#00e676")),   # Front Right: Green
            (-1.42, 1.08, QColor("#ff1744")),  # Front Left: Red
            (-1.42, -1.08, QColor("#ff1744")), # Rear Left: Red
            (1.42, -1.08, QColor("#00e676")),  # Rear Right: Green
        ]

        for mx, my, led_col in arm_params:
            rx = 0.36 if mx > 0 else -0.36
            ry = 0.28 if my > 0 else -0.28
            dx, dy = (mx - rx), (my - ry)
            length = sqrt(dx * dx + dy * dy)
            nx = -dy / length * 0.08
            ny = dx / length * 0.08

            # Arm 3D box vertices
            ab = [
                (rx - nx, ry - ny, 0.10), (rx + nx, ry + ny, 0.10),
                (mx + nx * 0.8, my + ny * 0.8, 0.16), (mx - nx * 0.8, my - ny * 0.8, 0.16),
                (rx - nx, ry - ny, 0.20), (rx + nx, ry + ny, 0.20),
                (mx + nx * 0.8, my + ny * 0.8, 0.24), (mx - nx * 0.8, my - ny * 0.8, 0.24),
            ]
            arm_faces = [
                ([4, 5, 6, 7], "arm_top", QColor("#1e252c")),
                ([0, 3, 2, 1], "arm_bot", QColor("#12171c")),
                ([0, 4, 7, 3], "arm_side", QColor("#181e24")),
                ([1, 2, 6, 5], "arm_side", QColor("#1b2228")),
            ]
            arms.append((ab, arm_faces))
            motors.append((mx, my, 0.26))
            rotors.append((mx, my, 0.35))
            nav_leds.append(((mx, my, 0.10), led_col))

        # Landing skids
        gear = [
            ((-0.52, -0.38, 0.04), (-0.60, -0.45, -0.36)),
            ((-0.52, 0.38, 0.04), (-0.60, 0.45, -0.36)),
            ((-0.60, -0.52, -0.36), (-0.60, 0.52, -0.36)),

            ((0.52, -0.38, 0.04), (0.60, -0.45, -0.36)),
            ((0.52, 0.38, 0.04), (0.60, 0.45, -0.36)),
            ((0.60, -0.52, -0.36), (0.60, 0.52, -0.36)),
        ]

        # Gimbal 4K Camera
        camera_pts = {
            "mount": (0.0, 0.52, -0.02),
            "body": (0.0, 0.62, -0.12),
            "lens": (0.0, 0.74, -0.12),
        }

        return v, faces, arms, motors, rotors, nav_leds, gear, camera_pts

    def _visual_yaw(self):
        """Convert compass heading to the math angle used by Rz."""
        return -float(self.heading) % 360.0

    # ------------------------------------------------------------------
    # 3D Shading & Face Lighting
    # ------------------------------------------------------------------
    def _shade_face(self, pts3, base_color):
        if len(pts3) < 3:
            return base_color, base_color

        v0, v1, v2 = pts3[0], pts3[1], pts3[2]
        d1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        d2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        normal = self._normalize_vec(self._cross_product(d1, d2))

        # Diffuse component
        diffuse = max(0.0, self._dot_product(normal, self._light_dir))
        intensity = 0.35 + 0.65 * diffuse

        # Specular highlight
        spec = 0.0
        if diffuse > 0.0:
            dot_nl = self._dot_product(normal, self._light_dir)
            ref = (
                2.0 * dot_nl * normal[0] - self._light_dir[0],
                2.0 * dot_nl * normal[1] - self._light_dir[1],
                2.0 * dot_nl * normal[2] - self._light_dir[2],
            )
            spec_dot = max(0.0, self._dot_product(self._normalize_vec(ref), (0.0, -0.5, 0.85)))
            spec = (spec_dot ** 6) * 0.32

        r = min(255, int(base_color.red() * intensity + 255 * spec))
        g = min(255, int(base_color.green() * intensity + 255 * spec))
        b = min(255, int(base_color.blue() * intensity + 255 * spec))

        edge_r = min(255, int(r * 1.30 + 25))
        edge_g = min(255, int(g * 1.30 + 25))
        edge_b = min(255, int(b * 1.30 + 25))

        return QColor(r, g, b), QColor(edge_r, edge_g, edge_b, 150)

    # ------------------------------------------------------------------
    # Rendering 3D Drone Mesh
    # ------------------------------------------------------------------
    def _draw_mesh(self, p, center, scale, pos):
        v, faces, arms, motors, rotors, nav_leds, gear, camera_pts = self._mesh()
        roll = max(-65.0, min(65.0, self.roll))
        pitch = max(-55.0, min(55.0, self.pitch))
        yaw = self._visual_yaw()

        def world(pt):
            return self._add(pos, self._rot(pt, roll, pitch, yaw))

        # 1. Depth-sorted 3D Polygon Rendering
        render_queue = []

        for ids, kind, base_col in faces:
            pts3 = [world(v[i]) for i in ids]
            proj = [self._project(q, center, scale) for q in pts3]
            depth = sum(q[1] for q in proj) / len(proj)
            fill_col, edge_col = self._shade_face(pts3, base_col)
            render_queue.append((depth, [q[0] for q in proj], fill_col, edge_col))

        for arm_box, arm_face_list in arms:
            for ids, kind, base_col in arm_face_list:
                pts3 = [world(arm_box[i]) for i in ids]
                proj = [self._project(q, center, scale) for q in pts3]
                depth = sum(q[1] for q in proj) / len(proj)
                fill_col, edge_col = self._shade_face(pts3, base_col)
                render_queue.append((depth, [q[0] for q in proj], fill_col, edge_col))

        # Sort polygons from back to front
        render_queue.sort(key=lambda item: item[0])
        for _, pts, fill_col, edge_col in render_queue:
            poly = QPolygonF(pts)
            p.setBrush(fill_col)
            p.setPen(QPen(edge_col, max(1, int(scale * 0.05))))
            p.drawPolygon(poly)

        # 2. Landing Gear
        p.setPen(QPen(QColor("#2b353e"), max(2, int(scale * 0.08)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in gear:
            qa = self._project(world(a), center, scale)[0]
            qb = self._project(world(b), center, scale)[0]
            p.drawLine(qa, qb)

        # 3. Gimbal Camera with Glass Lens Reflection
        g_mount = self._project(world(camera_pts["mount"]), center, scale)[0]
        g_body = self._project(world(camera_pts["body"]), center, scale)[0]
        g_lens = self._project(world(camera_pts["lens"]), center, scale)[0]

        p.setPen(QPen(QColor("#28343f"), max(2, int(scale * 0.07))))
        p.drawLine(g_mount, g_body)

        cam_r = max(3.5, scale * 0.20)
        p.setBrush(QColor("#182028"))
        p.setPen(QPen(QColor("#455668"), max(1, int(scale * 0.03))))
        p.drawEllipse(g_body, cam_r, cam_r * 0.85)

        # 4K Glass Lens element
        lens_r = max(2.2, scale * 0.12)
        lens_grad = QRadialGradient(g_lens, lens_r)
        lens_grad.setColorAt(0.0, QColor("#56e0ff"))
        lens_grad.setColorAt(0.6, QColor("#0d5e7d"))
        lens_grad.setColorAt(1.0, QColor("#061720"))
        p.setBrush(lens_grad)
        p.setPen(QPen(QColor("#a8f2ff"), 1))
        p.drawEllipse(g_lens, lens_r, lens_r * 0.72)

        # 4. Brushless Motors, Anodized Prop Nuts & Dynamic Spinning Blades
        for idx, motor in enumerate(motors):
            m3 = world(motor)
            q, _ = self._project(m3, center, scale)

            # Motor bell
            bell_r = max(4.0, scale * 0.26)
            bell_ry = bell_r * 0.52
            p.setBrush(QColor("#1d252e"))
            p.setPen(QPen(QColor("#4e6072"), max(1, int(scale * 0.04))))
            p.drawEllipse(q, bell_r, bell_ry)

            # Copper coil ring
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#d47c2a"), 1))
            p.drawEllipse(q, bell_r * 0.75, bell_ry * 0.75)

            # Propeller spinner nut (Orange CW / Blue CCW)
            nut_col = QColor("#ff6b22") if idx in (0, 2) else QColor("#00d2ff")
            p.setBrush(nut_col)
            p.setPen(QPen(QColor("#ffffff"), 1))
            p.drawEllipse(q, max(2.0, scale * 0.08), max(1.5, scale * 0.06))

            # Rotor Blades
            r3 = world(rotors[idx])
            rq, _ = self._project(r3, center, scale)
            prop_r = max(18.0, scale * 1.25)
            prop_ry = prop_r * 0.38

            spin_dir = 1 if idx in (0, 2) else -1
            blade_ang = radians(self._prop_angle * spin_dir + idx * 90.0)

            if self._prop_speed > 0.30:
                # High-speed semi-transparent prop-wash disc
                disc_alpha = int(40 + 105 * self._prop_speed)
                p.setPen(QPen(QColor(160, 210, 240, int(disc_alpha * 0.65)), max(1, int(scale * 0.03))))
                p.setBrush(QColor(110, 170, 220, int(disc_alpha * 0.20)))
                p.drawEllipse(rq, prop_r, prop_ry)

                # Yellow safety tip ring
                p.setPen(QPen(QColor(255, 215, 0, int(disc_alpha * 0.85)), max(1, int(scale * 0.05))))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(rq, prop_r * 0.95, prop_ry * 0.95)

                # Spinning blade streak
                streak_dx = cos(blade_ang) * prop_r * 0.88
                streak_dy = sin(blade_ang) * prop_ry * 0.88
                p.setPen(QPen(QColor(255, 255, 255, int(disc_alpha * 0.9)), max(2, int(scale * 0.06))))
                p.drawLine(QPointF(rq.x() - streak_dx, rq.y() - streak_dy), QPointF(rq.x() + streak_dx, rq.y() + streak_dy))
            else:
                # Foldable carbon blades at rest
                dx = cos(blade_ang) * prop_r * 0.90
                dy = sin(blade_ang) * prop_ry * 0.90
                p.setPen(QPen(QColor("#26303a"), max(2, int(scale * 0.10)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(QPointF(rq.x() - dx, rq.y() - dy), QPointF(rq.x() + dx, rq.y() + dy))

                # Safety yellow tip stripes
                p.setPen(QPen(QColor("#ffd600"), max(2, int(scale * 0.11)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(QPointF(rq.x() + dx * 0.75, rq.y() + dy * 0.75), QPointF(rq.x() + dx * 0.95, rq.y() + dy * 0.95))
                p.drawLine(QPointF(rq.x() - dx * 0.75, rq.y() - dy * 0.75), QPointF(rq.x() - dx * 0.95, rq.y() - dy * 0.95))

        # 5. Aviation Navigation LEDs (Port Red / Starboard Green)
        for led_pos, led_col in nav_leds:
            l_screen, _ = self._project(world(led_pos), center, scale)
            led_r = max(2.5, scale * 0.08)

            glow = QRadialGradient(l_screen, led_r * 3.0)
            glow.setColorAt(0.0, QColor(led_col.red(), led_col.green(), led_col.blue(), 230))
            glow.setColorAt(0.4, QColor(led_col.red(), led_col.green(), led_col.blue(), 90))
            glow.setColorAt(1.0, QColor(led_col.red(), led_col.green(), led_col.blue(), 0))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(l_screen, led_r * 3.0, led_r * 3.0)

            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(l_screen, led_r * 0.7, led_r * 0.7)

        # 6. Prominent 3D Forward Heading Beam & Arrow (Tia chỉ hướng đầu Drone)
        # Front searchlights & light cone
        light_left = world((-0.20, 0.70, 0.12))
        light_right = world((0.20, 0.70, 0.12))
        cone_left = world((-0.75, 2.80, -0.05))
        cone_right = world((0.75, 2.80, -0.05))

        q_ll = self._project(light_left, center, scale)[0]
        q_lr = self._project(light_right, center, scale)[0]
        q_cl = self._project(cone_left, center, scale)[0]
        q_cr = self._project(cone_right, center, scale)[0]

        # Dual beam projection cone
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 240, 255, 22))
        poly_cone = QPolygonF([q_ll, q_cl, q_cr, q_lr])
        p.drawPolygon(poly_cone)

        # 3D Main Forward Laser Vector
        nose_start = self._project(world((0, 0.50, 0.22)), center, scale)[0]
        nose_tip = self._project(world((0, 2.80, 0.22)), center, scale)[0]
        nose_left = self._project(world((-0.42, 2.30, 0.22)), center, scale)[0]
        nose_right = self._project(world((0.42, 2.30, 0.22)), center, scale)[0]
        nose_inner = self._project(world((0, 2.40, 0.22)), center, scale)[0]

        # Outer glow line
        p.setPen(QPen(QColor(0, 240, 255, 85), max(4, int(scale * 0.16)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(nose_start, nose_tip)
        # Inner neon core line
        p.setPen(QPen(QColor("#00f0ff"), max(2, int(scale * 0.08)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(nose_start, nose_tip)

        # 3D Arrowhead
        p.setBrush(QColor("#00f0ff"))
        p.setPen(QPen(QColor("#ffffff"), 1))
        arrow_head = QPolygonF([nose_tip, nose_left, nose_inner, nose_right])
        p.drawPolygon(arrow_head)

        # Forward Chevrons on body beam
        for chevron_y in (1.15, 1.75):
            c_tip = self._project(world((0, chevron_y + 0.22, 0.22)), center, scale)[0]
            c_l = self._project(world((-0.24, chevron_y, 0.22)), center, scale)[0]
            c_r = self._project(world((0.24, chevron_y, 0.22)), center, scale)[0]
            p.setPen(QPen(QColor(255, 255, 255, 220), max(1, int(scale * 0.05)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(c_l, c_tip)
            p.drawLine(c_r, c_tip)

        # Canopy High-Visibility Directional Triangle Badge (Fluorescent Yellow-Green)
        canopy_tip = self._project(world((0, 0.50, 0.36)), center, scale)[0]
        canopy_l = self._project(world((-0.20, 0.05, 0.38)), center, scale)[0]
        canopy_r = self._project(world((0.20, 0.05, 0.38)), center, scale)[0]
        p.setBrush(QColor("#ffd600"))
        p.setPen(QPen(QColor("#ffffff"), 1))
        p.drawPolygon(QPolygonF([canopy_tip, canopy_l, canopy_r]))

        # Front Heading Label badge in 3D
        p.setFont(QFont("Segoe UI", max(8, int(scale * 0.36)), QFont.Weight.Bold))
        p.setPen(QColor("#00f0ff"))
        p.drawText(int(nose_tip.x() + 8), int(nose_tip.y() + 4), "MŨI TRƯỚC (FWD)")

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

        # Top-Right Tactical Aviation Compass & Heading Dial
        cx = w - 48
        cy = 48
        cr = 28
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(11, 22, 34, 215))
        p.drawEllipse(QPointF(cx, cy), cr + 5, cr + 5)

        # Compass outer bezel
        p.setPen(QPen(QColor(56, 82, 108, 190), 1.5))
        p.drawEllipse(QPointF(cx, cy), cr, cr)

        # Cardinal markings
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.setPen(QColor("#ff4757"))
        p.drawText(cx - 3, cy - cr + 9, "N")
        p.setPen(QColor("#7f91a5"))
        p.setFont(QFont("Segoe UI", 6))
        p.drawText(cx + cr - 8, cy + 3, "E")
        p.drawText(cx - 2, cy + cr - 3, "S")
        p.drawText(cx - cr + 3, cy + 3, "W")

        # Rotating Drone Heading Needle (Pointing along self.heading)
        p.save()
        p.translate(cx, cy)
        p.rotate(self.heading)

        # Cyan needle (Front / Nose)
        p.setBrush(QColor("#00f0ff"))
        p.setPen(QPen(QColor("#ffffff"), 1))
        p.drawPolygon(QPolygonF([QPointF(0, -cr + 4), QPointF(-3.5, 0), QPointF(0, -2.5), QPointF(3.5, 0)]))
        # Red needle (Rear / Tail)
        p.setBrush(QColor("#ff4757"))
        p.drawPolygon(QPolygonF([QPointF(0, cr - 8), QPointF(-2.5, 0), QPointF(0, 2.5), QPointF(2.5, 0)]))
        p.restore()

        # Digital Heading readout below compass
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(QColor("#00f0ff"))
        p.drawText(cx - 18, cy + cr + 14, f"HDG {int(self.heading):03d}°")

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

            # Ground shadow & Ground Forward Heading track projected at aircraft's XY position.
            ground_pos = (east, north, 0.0)
            ground_screen = self._project(ground_pos, center, scale)[0]
            shadow = max(5.0, 18.0 - min(altitude, 18.0) * 0.6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 95))
            p.drawEllipse(ground_screen, shadow * 1.5, shadow * 0.45)

            # Ground forward heading vector (shows ground track compass direction)
            h_rad = radians(self.heading)
            g_fwd_east = east + 3.0 * sin(h_rad)
            g_fwd_north = north + 3.0 * cos(h_rad)
            g_fwd_screen = self._project((g_fwd_east, g_fwd_north, 0.0), center, scale)[0]

            # Ground heading laser dashed line and arrow point
            p.setPen(QPen(QColor(0, 240, 255, 120), max(1, int(scale * 0.06)), Qt.PenStyle.DashLine))
            p.drawLine(ground_screen, g_fwd_screen)
            p.setBrush(QColor("#00f0ff"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(g_fwd_screen, max(2.0, scale * 0.07), max(2.0, scale * 0.07))

            self._draw_mesh(p, center, scale, pos)

            distance = sqrt(east * east + north * north + altitude * altitude)
            self._draw_overlay(p, w, h, scale / 2.5, distance)
        finally:
            p.end()
