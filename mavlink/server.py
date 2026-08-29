import socket, threading, time, math, inspect
from pymavlink.dialects.v20.ardupilotmega import MAVLink
from pymavlink import mavutil

from .mav_logger import mav_log, CONN, TX, RX, PARSE, COMMAND

class MAVLinkServer:
    """Windows-safe MAVLink UDP server using raw UDP sockets and pymavlink encoders."""
    def __init__(self,state,tx_host='127.0.0.1',tx_port=14550,rx_host='0.0.0.0',rx_port=14551,rate_hz=20):
        self.s=state; self.tx_host=tx_host; self.tx_port=int(tx_port); self.rx_host=rx_host; self.rx_port=int(rx_port); self.rate=float(rate_hz)
        self.running=False; self.thread=None; self.client_addr=None
        self.tx=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.rx=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.rx.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); self.rx.bind((self.rx_host,self.rx_port)); self.rx.setblocking(False)
        self.mav=MAVLink(None); self.mav.srcSystem=1; self.mav.srcComponent=1
        self.parser=MAVLink(None); self.parser.srcSystem=255; self.parser.srcComponent=190

    def start(self):
        if self.running:return
        self.running=True; self.s.running=True; self.thread=threading.Thread(target=self.loop,daemon=True,name='RIGEL-MAVLink'); self.thread.start()
        mav_log.info(CONN, f'TX -> {self.tx_host}:{self.tx_port} | RX <- {self.rx_host}:{self.rx_port}')
    def stop(self):
        self.running=False; self.s.running=False
        for sock in (self.rx,self.tx):
            try:sock.close()
            except OSError:pass

    def _field_value(self,name,s):
        # Dynamic field mapping makes this compatible with pymavlink dialect versions
        if name in ('time_boot_ms','time_boot'): return s.boot_ms()
        if name in ('time_usec','time_us'): return s.boot_us()
        if name=='lat': return int(s.lat*1e7)
        if name=='lon': return int(s.lon*1e7)
        if name in ('alt','altitude'): return int(s.alt*1000) if name=='alt' else s.alt
        if name=='relative_alt': return int(s.agl*1000)
        if name in ('x','y','z'): return {'x':0.0,'y':0.0,'z':-s.alt}[name]
        if name=='vx': return int(s.vx*100) if 'position_int' in self._current_msg else s.vx
        if name=='vy': return int(s.vy*100) if 'position_int' in self._current_msg else s.vy
        if name=='vz': return int(s.vz*100) if 'position_int' in self._current_msg else s.vz
        if name in ('hdg','heading'): return int(s.heading*100) if name=='hdg' else s.heading
        if name in ('roll','pitch','yaw'): return math.radians(getattr(s,name))
        if name in ('rollspeed','pitchspeed','yawspeed'): return {'rollspeed':s.gyro_x,'pitchspeed':s.gyro_y,'yawspeed':s.gyro_z}[name]
        if name in ('groundspeed','ground_speed'): return s.ground_speed
        if name=='airspeed': return s.air_speed
        if name in ('climb','vertical_speed'): return s.vertical_speed
        if name=='throttle': return int(s.throttle)
        if name=='fix_type': return s.gps_fix
        if name=='satellites_visible': return s.satellites
        if name in ('eph','hdop'): return int(s.hdop*100)
        if name in ('epv','vdop'): return int(s.vdop*100)
        if name in ('h_acc','hacc'): return int(s.hacc*1000)
        if name in ('v_acc','vacc'): return int(s.vacc*1000)
        if name in ('vel','gps_speed'): return int(s.gps_speed*100)
        if name=='cog': return int(s.heading*100)
        if name in ('pressure','abs_pressure','press_abs'): return s.pressure
        if name in ('diff_pressure','press_diff'): return 0.0
        if name in ('pressure_alt','press_alt'): return s.alt
        if name in ('temperature','temp'): return s.temperature
        if name in ('xacc','accel_x'): return s.accel_x
        if name in ('yacc','accel_y'): return s.accel_y
        if name in ('zacc','accel_z'): return s.accel_z
        if name in ('xgyro','gyro_x'): return s.gyro_x
        if name in ('ygyro','gyro_y'): return s.gyro_y
        if name in ('zgyro','gyro_z'): return s.gyro_z
        if name in ('xmag','mag_x'): return s.mag_x
        if name in ('ymag','mag_y'): return s.mag_y
        if name in ('zmag','mag_z'): return s.mag_z
        if name=='voltage_battery': return int(s.battery_voltage*1000)
        if name in ('current_battery','current'): return int(s.battery_current*100)
        if name=='battery_remaining': return int(max(0,min(100,s.battery_remaining)))
        if name=='current_consumed': return int(s.battery_consumed)
        if name=='energy_consumed': return int(s.battery_consumed*s.battery_voltage)
        if name in ('temperature_battery','battery_temperature'): return int(s.battery_temperature*100)
        if name=='voltages': return s.cell_voltages+[65535]*6
        if name=='voltages_ext': return [0,0,0,0]
        if name=='chan_count' or name=='chancount': return 16
        if name.startswith('chan') and name.endswith('_raw'):
            try:return s.rc[int(name[4:name.index('_raw')])-1]
            except:return 0
        if name=='rssi': return 255 if s.rc_ok else 0
        if name=='current_distance': return int(max(0,s.rangefinder)*100)
        if name=='min_distance': return 20
        if name=='max_distance': return 20000
        if name=='distance_home': return int(s.distance_home)
        if name=='wp_dist': return int(s.distance_home)
        if name=='alt_error': return s.target_alt-s.alt
        if name in ('nav_bearing','target_bearing'): return int(s.heading)
        if name=='nav_roll': return s.roll
        if name=='nav_pitch': return s.pitch
        if name=='aspd_error': return s.air_speed-s.ground_speed
        if name=='xtrack_error': return 0.0
        if name=='landed_state': return mavutil.mavlink.MAV_LANDED_STATE_ON_GROUND if s.landed else mavutil.mavlink.MAV_LANDED_STATE_IN_AIR
        if name=='vtol_state': return mavutil.mavlink.MAV_VTOL_STATE_UNDEFINED
        if name=='battery_id': return 1
        if name=='id': return 1
        if name=='battery_function': return mavutil.mavlink.MAV_BATTERY_FUNCTION_ALL
        if name=='type': return mavutil.mavlink.MAV_BATTERY_TYPE_LIPO
        if name=='temperature': return s.temperature
        if name=='charge_state': return mavutil.mavlink.MAV_BATTERY_CHARGE_STATE_OK
        if name=='time_remaining': return 0
        if name=='mode': return 0
        if name=='fault_bitmask': return 0
        if name=='current_battery': return int(s.battery_current*100)
        if name=='system_id': return 1
        if name=='component_id': return 1
        if name=='target_system': return 255
        if name=='target_component': return 190
        if name=='progress': return 0
        if name=='result_param2': return 0
        if name=='param_id': return b'SIM_SPEED\\0'
        if name=='param_value': return 1.0
        if name=='param_type': return mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        if name=='param_count': return 1
        if name=='param_index': return 0
        return None

    def _encode(self,name,**overrides):
        fn=getattr(self.mav,name+'_encode')
        self._current_msg=name
        sig=inspect.signature(fn)
        args=[]
        with self.s.lock:s=self.s
        for p in sig.parameters.values():
            if p.name in overrides: v=overrides[p.name]
            else:v=self._field_value(p.name,s)
            if v is None:
                if p.default is not inspect.Parameter.empty:v=p.default
                elif 'flags' in p.name or p.name in ('custom_mode','base_mode'):v=0
                elif p.name in ('type','id','orientation','covariance','system_id','component_id','target_system','target_component'):v=0
                elif 'array' in p.name or p.name.startswith('voltages'):v=[]
                else:v=0
            args.append(v)
        return fn(*args)

    def send(self,msg):
        try:self.tx.sendto(msg.pack(self.mav),(self.tx_host,self.tx_port))
        except OSError as e: mav_log.error(TX, f'UDP TX error: {e!r}')
        except Exception as e: mav_log.error(TX, f'{type(e).__name__}: {e}')

    def heartbeat(self):
        with self.s.lock: armed=self.s.armed
        base=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED | (mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED if armed else 0)
        self.send(self._encode('heartbeat',type=mavutil.mavlink.MAV_TYPE_QUADROTOR,autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,base_mode=base,custom_mode=0,system_status=mavutil.mavlink.MAV_STATE_ACTIVE))

    def send_telemetry(self):
        names=['system_time','global_position_int','local_position_ned','attitude','vfr_hud','gps_raw_int','sys_status','battery_status','highres_imu','distance_sensor','rc_channels','nav_controller_output','extended_sys_state']
        for n in names:
            try:self.send(self._encode(n))
            except Exception as e: mav_log.error(TX, f'{n}: {type(e).__name__}: {e}')

    def receive(self):
        while True:
            try:data,addr=self.rx.recvfrom(8192)
            except BlockingIOError:return
            except OSError:return
            self.client_addr=addr
            for b in data:
                try:
                    msg=self.parser.parse_char(bytes([b]))
                    if msg:self.handle(msg)
                except Exception as e: mav_log.error(PARSE, f'{type(e).__name__}: {e}')

    def ack(self,cmd,result=0):
        try:self.send(self._encode('command_ack',command=cmd,result=result))
        except Exception as e: mav_log.error(COMMAND, f'ACK error: {e}')

    def handle(self,msg):
        t=msg.get_type(); s=self.s
        with s.lock:
            if t=='COMMAND_LONG':
                c=msg.command
                if c==mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                    s.armed=msg.param1>=0.5; s.last_command='ARM' if s.armed else 'DISARM'; s.system_status=4 if s.armed else 3; self.ack(c)
                elif c==mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
                    s.target_alt=max(1.0,float(msg.param7 or 20)); s.mode='TAKEOFF'; s.armed=True; s.last_command='TAKEOFF'; self.ack(c)
                elif c==mavutil.mavlink.MAV_CMD_NAV_LAND:s.mode='LAND';s.last_command='LAND';self.ack(c)
                elif c==mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH:s.mode='RTL';s.last_command='RTL';self.ack(c)
                elif c==mavutil.mavlink.MAV_CMD_DO_SET_MODE:s.mode='GUIDED';s.last_command='SET_MODE';self.ack(c)
                else:self.ack(c,mavutil.mavlink.MAV_RESULT_UNSUPPORTED)
            elif t=='SET_MODE':s.mode='GUIDED';s.last_command='SET_MODE'
            elif t=='RC_CHANNELS_OVERRIDE':
                for i in range(1,9):
                    n=f'chan{i}_raw';
                    if hasattr(msg,n):s.rc[i-1]=getattr(msg,n)
            elif t=='MISSION_CLEAR_ALL':s.mission=[];s.wp_index=0;s.mission_active=False

    def loop(self):
        last=time.monotonic();hb=0
        while self.running:
            try:
                now=time.monotonic();dt=now-last;last=now
                fm=getattr(self.s,'flight_model',None)
                if fm:fm.update(dt)
                self.receive();hb+=dt
                if hb>=1:self.heartbeat();hb=0
                self.send_telemetry()
            except Exception as e: mav_log.error(CONN, f'loop error: {type(e).__name__}: {e}')
            time.sleep(max(0.005,1/self.rate))
