"""Deterministic camera simulator for mission execution."""

import json
import os
import struct
import math
from typing import Any, Dict, Optional


class CameraSimulator:
    """Simulates a mapping camera and writes a small image + metadata."""

    def __init__(self, drone=None, output_dir: Optional[str] = None):
        self.drone = drone
        self.output_dir = output_dir or os.path.join(os.getcwd(), "simulation_data", "photos")
        os.makedirs(self.output_dir, exist_ok=True)
        self.capture_count = 0
        self.enabled = True
        self.recording = False
        self.trigger_distance_m = 0.0
        self.last_capture: Optional[Dict[str, Any]] = None
        self._last_trigger_lat: Optional[float] = None
        self._last_trigger_lon: Optional[float] = None

    def capture(self, sim_time: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.capture_count += 1
        state = getattr(self.drone, "state", None)
        lat = float(getattr(state, "lat", 0.0))
        lon = float(getattr(state, "lon", 0.0))
        alt = float(getattr(state, "alt", 0.0))
        yaw = float(getattr(state, "yaw", 0.0))

        image_id = f"IMG_{self.capture_count:06d}"
        image_path = os.path.join(self.output_dir, image_id + ".bmp")
        meta_path = os.path.join(self.output_dir, image_id + ".json")

        self._write_bmp(image_path, image_id, lat, lon, alt)
        result = {
            "image_id": image_id,
            "image_path": os.path.abspath(image_path),
            "metadata_path": os.path.abspath(meta_path),
            "sim_time": float(sim_time),
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "yaw": yaw,
            "metadata": dict(metadata or {}),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        self.last_capture = result
        print(f"[CAMERA] CAPTURE {image_id} LAT={lat:.7f} LON={lon:.7f} ALT={alt:.2f}")
        return result

    def update(self, sim_time: float = 0.0) -> None:
        """Trigger mapping photos while the drone travels the configured distance."""
        if not self.enabled or self.trigger_distance_m <= 0.0:
            return
        state = getattr(self.drone, "state", None)
        if state is None:
            return
        lat = float(getattr(state, "lat", 0.0))
        lon = float(getattr(state, "lon", 0.0))
        if self._last_trigger_lat is None:
            self._last_trigger_lat, self._last_trigger_lon = lat, lon
            return
        distance = self._distance_m(self._last_trigger_lat, self._last_trigger_lon, lat, lon)
        if distance >= self.trigger_distance_m:
            self.capture(sim_time=sim_time, metadata={"trigger": "DISTANCE", "distance_m": distance})
            self._last_trigger_lat, self._last_trigger_lon = lat, lon

    @staticmethod
    def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371000.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2.0 * r * math.asin(math.sqrt(max(0.0, min(1.0, a))))

    def start_recording(self) -> bool:
        self.recording = True
        print("[CAMERA] RECORDING START")
        return True

    def stop_recording(self) -> bool:
        self.recording = False
        print("[CAMERA] RECORDING STOP")
        return True

    def set_trigger_distance(self, distance_m: float) -> bool:
        self.trigger_distance_m = max(0.0, float(distance_m))
        self._last_trigger_lat = None
        self._last_trigger_lon = None
        print(f"[CAMERA] TRIGGER DISTANCE = {self.trigger_distance_m:.2f} m")
        return True

    @staticmethod
    def _write_bmp(path: str, image_id: str, lat: float, lon: float, alt: float) -> None:
        # Simple 320x240 24-bit BMP generated without external image packages.
        width, height = 320, 240
        row_size = (width * 3 + 3) & ~3
        pixel_size = row_size * height
        file_size = 54 + pixel_size
        with open(path, "wb") as f:
            f.write(b"BM")
            f.write(struct.pack("<IHHI", file_size, 0, 0, 54))
            f.write(struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, pixel_size, 2835, 2835, 0, 0))
            for y in range(height):
                for x in range(width):
                    # Deterministic synthetic aerial image pattern.
                    r = (x * 255) // width
                    g = (y * 255) // height
                    b = 120 + ((x + y) % 80)
                    f.write(bytes((b, g, r)))
                f.write(b"\x00" * (row_size - width * 3))
