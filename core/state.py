import threading
import time


class DroneState:

    def __init__(
        self,
        lat=10.8231000,
        lon=106.6297000,
        alt=0.0,
    ):

        self.lock = threading.RLock()

        self.started = time.monotonic()

        # ====================================================
        # SYSTEM
        # ====================================================

        self.running = False

        self.sim_time = 0.0

        # ====================================================
        # POSITION
        # ====================================================

        self.lat = float(lat)

        self.lon = float(lon)

        self.alt = float(alt)

        # ====================================================
        # VELOCITY
        # ====================================================

        self.ground_speed = 0.0

        self.vertical_speed = 0.0

        self.north_speed = 0.0

        self.east_speed = 0.0

        # ====================================================
        # ATTITUDE
        # ====================================================

        self.heading = 0.0

        self.roll = 0.0

        self.pitch = 0.0

        self.yaw = 0.0

        # ====================================================
        # FLIGHT
        # ====================================================

        self.mode = "STANDBY"

        self.armed = False

        self.airborne = False

        # ====================================================
        # BATTERY
        # ====================================================

        self.battery = 100.0

        self.voltage = 16.8

        self.current = 0.0

        # ====================================================
        # GPS
        # ====================================================

        self.gps_fix = 3

        self.satellites = 12

        self.gps_hdop = 1.0

        self.gps_vdop = 1.0

    # ========================================================
    # GET STATUS
    # ========================================================

    def get_status(self):

        with self.lock:

            return {

                "lat": self.lat,

                "lon": self.lon,

                "alt": self.alt,

                "ground_speed":
                    self.ground_speed,

                "vertical_speed":
                    self.vertical_speed,

                "north_speed":
                    self.north_speed,

                "east_speed":
                    self.east_speed,

                "heading":
                    self.heading,

                "roll":
                    self.roll,

                "pitch":
                    self.pitch,

                "yaw":
                    self.yaw,

                "mode":
                    self.mode,

                "armed":
                    self.armed,

                "airborne":
                    self.airborne,

                "battery":
                    self.battery,

                "voltage":
                    self.voltage,

                "current":
                    self.current,

                "gps_fix":
                    self.gps_fix,

                "satellites":
                    self.satellites,

                "gps_hdop":
                    self.gps_hdop,

                "gps_vdop":
                    self.gps_vdop,

                "sim_time":
                    self.sim_time,
            }