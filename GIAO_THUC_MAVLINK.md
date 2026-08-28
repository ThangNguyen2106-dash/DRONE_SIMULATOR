# Giao thức MAVLink trong RIGEL UAV Drone Simulator

Tài liệu mô tả chi tiết cách simulator triển khai giao thức MAVLink, đi từ tầng vận chuyển
(transport) → tầng đóng gói (frame) → luồng phiên làm việc (session) → nội dung từng nhóm message.
Dựa trên mã nguồn thực tế trong `mavlink/connection.py`, `mavlink/telemetry.py`,
`mavlink/messages.py`, `mavlink/command_receiver.py`, `mavlink/mission_receiver.py` và cách
`gui/simulation_worker.py` khởi tạo/chạy các thành phần này.

> **Lưu ý:** repo còn một file `mavlink/server.py` cài đặt một MAVLink server kiểu khác (dùng
> `pymavlink.dialects.v20.ardupilotmega.MAVLink` trực tiếp, tự chạy thread riêng). File này
> **không được `SimulationWorker` sử dụng** trong luồng chạy hiện tại của ứng dụng — luồng chính
> thức là `MAVLinkConnection` + `MAVLinkTelemetry` + `CommandReceiver` + `MissionReceiver` như mô
> tả dưới đây. `mavlink/server.py` được coi là một cài đặt thay thế/legacy, không nên xem là hành
> vi runtime hiện tại.

## 1. Tầng vận chuyển (Transport Layer)

- **Giao thức mạng:** UDP, dùng `socket.socket(AF_INET, SOCK_DGRAM)` chuẩn của Python
  (`mavlink/connection.py`), **không** dùng `mavutil.mavlink_connection()`.
- **1 socket dùng chung cho cả RX và TX:** socket được `bind()` vào địa chỉ RX cục bộ
  (`rx_host:rx_port`), sau đó set `setblocking(False)` để poll non-blocking trong vòng lặp mô
  phỏng.
- **Chuỗi kết nối (`connection_string`):** dạng `udp:<host>:<port>` (hoặc `udpout:` / `udpin:`,
  được parse nhưng xử lý y hệt `udp:`). Do `MAVLinkConfigPanel` build sẵn
  `connection_string = f"udp:0.0.0.0:{port}"`, port RX cục bộ và port TX mặc định trong cấu hình
  GUI dùng chung một số hiệu cổng (`Port` trên UI).
- **Địa chỉ đích khi gửi (TX):** ưu tiên theo thứ tự
  1. `address` truyền thẳng vào `send()` (không dùng trong luồng hiện tại),
  2. `last_rx_address` — địa chỉ UDP của gói tin GCS gần nhất nhận được,
  3. `tx_address` — địa chỉ mặc định lấy từ `connection_string`.

  Nói cách khác: **simulator tự học địa chỉ GCS** từ gói tin đầu tiên nhận được và trả lời đúng
  cổng nguồn đó, thay vì gửi cứng tới một cổng cấu hình.
- **`config/simulator.json`** chỉ là cấu hình mặc định tham khảo (không được `MAVLinkConfigPanel`
  đọc trực tiếp khi khởi động GUI):
  ```json
  {
    "system_id": 1,
    "component_id": 1,
    "tx_host": "127.0.0.1",
    "tx_port": 14550,
    "rx_host": "0.0.0.0",
    "rx_port": 14551,
    "telemetry_rate_hz": 20,
    "home": {"lat": 10.8231, "lon": 106.6297, "alt": 0.0}
  }
  ```

## 2. Tầng đóng gói (Frame / Encoding Layer)

- **Encode/decode message** dựa trên `pymavlink.mavutil.mavlink.MAVLink` (dialect mặc định của
  `pymavlink`, thường là ArduPilot/common dialect tuỳ bản cài).
- Mỗi `MAVLinkConnection` sở hữu một instance `MAVLink(None)` riêng
  (`self.mavlink = mavutil.mavlink.MAVLink(None)`), gán:
  - `srcSystem = source_system` (mặc định 1, lấy từ System ID cấu hình GUI)
  - `srcComponent = source_component` (mặc định 1, lấy từ Component ID cấu hình GUI)
- **Gửi (`send`):** message được build bằng các hàm `<msg>_encode(...)` do `pymavlink` sinh sẵn
  theo dialect, sau đó `message.pack(self.mavlink)` ra bytes, rồi `socket.sendto()`.
- **Nhận (`receive` / `_parse_packet`):** dữ liệu UDP thô được đưa qua
  `self.mavlink.parse_char(bytes([byte]))` **từng byte một** — đây là bộ phân tích khung MAVLink
  chuẩn (magic byte, length, seq, sysid/compid, msgid, payload, checksum, ký hiệu v1/v2) do
  `pymavlink` xử lý nội bộ. Message hoàn chỉnh được đẩy vào hàng đợi `_rx_message_queue` (kiểu
  `deque`) để `SimulationWorker` lấy ra tuần tự bằng `receive(blocking=False)`.
- **Không có bước xác thực chữ ký MAVLink2 (signing)** — simulator chấp nhận mọi message hợp lệ về
  mặt cấu trúc, không kiểm tra `system_id`/`component_id` nguồn khi xử lý lệnh (ngoại trừ việc ghi
  nhớ để trả lời đúng địa chỉ).

## 3. Vòng đời phiên làm việc (Session Lifecycle)

Toàn bộ vòng đời do `gui/simulation_worker.py::SimulationWorker.run()` điều phối, chạy trên một
`QThread` riêng biệt với luồng GUI:

1. **Khởi tạo đối tượng mô phỏng:** `Drone` (trạng thái bay) → `FlightController`.
2. **Khởi tạo MAVLink:**
   - `MAVLinkConnection(connection_string, source_system, source_component)` → `.connect()`
     (bind UDP socket).
   - `MissionReceiver(connection, mission=drone.mission, system_id, component_id)`.
   - `CommandReceiver(connection, controller, drone)`.
   - `MAVLinkTelemetry(drone, connection, system_id, component_id)`.
3. **Phát tín hiệu `status_changed("READY")`** — lưu ý: `MainWindow.on_status_changed()` hiện chỉ
   xử lý `"RUNNING"` và `"STOPPED"`, nên trạng thái `"READY"` không làm đổi nhãn UI (label vẫn hiển
   thị `STARTING...` cho tới khi có cập nhật tiếp theo).
4. **Vòng lặp mô phỏng** (không giới hạn tần số cứng bằng `rate_hz`, chỉ `time.sleep(0.01)` mỗi
   vòng ⇒ ~100 Hz vòng lặp nội bộ, telemetry tự giới hạn tần số qua timer nội bộ ở bước tiếp theo):
   a. `_process_runtime_commands()` — áp các lệnh runtime từ GUI (ARM/DISARM/TAKEOFF/... khi các
      panel thủ công được gắn vào, xem `HUONG_DAN_SU_DUNG.md` mục 8).
   b. `mavlink.receive(blocking=False)` theo vòng `while` cho tới khi hàng đợi RX rỗng; mỗi message
      được đưa qua **cả** `mission_receiver.process(message)` **và** `command_receiver.process(message)`
      (không loại trừ lẫn nhau — mỗi receiver tự bỏ qua loại message nó không quan tâm).
   c. `drone.update(dt)` — cập nhật mô hình vật lý bay.
   d. `telemetry.update()` — gửi các message định kỳ theo tần số riêng từng loại (mục 5).
   e. `telemetry_updated.emit(drone.get_status())` — cập nhật UI (ALT/SPD/BAT).
5. **Dừng:** `stop()` set `self.running = False` → thoát vòng lặp → `_cleanup()` đóng
   `MAVLinkConnection`, giải phóng tham chiếu, phát `status_changed("STOPPED")`.

## 4. Nhận diện danh tính (Identity)

| Trường | Nguồn | Giá trị mặc định |
|---|---|---|
| `system_id` (vehicle) | `MAVLINK CONFIGURATION → System ID` | `1` |
| `component_id` (vehicle) | `MAVLINK CONFIGURATION → Component ID` | `1` |
| `target_system` khi trả lời | `sender_system` ghi nhớ từ message GCS gần nhất (mặc định `0` nếu chưa có) | — |
| `target_component` khi trả lời | `sender_component` tương tự | — |

`MissionReceiver._remember_sender()` gọi `message.get_srcSystem()` / `get_srcComponent()` mỗi khi
nhận được message liên quan tới mission, để các phản hồi (`MISSION_REQUEST_INT`,
`MISSION_COUNT`, `MISSION_ACK`, ...) gửi đúng `target_system/target_component` của GCS đang thao
tác.

## 5. Nội dung telemetry — chiều TX (Simulator → GCS)

`MAVLinkTelemetry.update()` dùng các timestamp `last_*` để tự giới hạn tần suất gửi, độc lập với
`Telemetry Rate` cấu hình trên GUI (giá trị đó chỉ được lưu, chưa được dùng để đổi các hằng số Hz
dưới đây trong `mavlink/telemetry.py`):

| Message | Tần số | Nội dung chính | Nguồn hàm build |
|---|---|---|---|
| `HEARTBEAT` | 1 Hz | `type=MAV_TYPE_QUADROTOR`, `autopilot=MAV_AUTOPILOT_ARDUPILOTMEGA`, `base_mode` (bật cờ `SAFETY_ARMED` nếu đang ARM), `system_status` (`ACTIVE`/`STANDBY`) | `MAVLinkMessages.heartbeat()` |
| `GLOBAL_POSITION_INT` | 10 Hz | `lat/lon` (độ × 1e7), `alt`/`relative_alt` (mm), vận tốc Bắc/Đông/Xuống (`vx/vy/vz`, cm/s, tính từ `ground_speed` + `yaw`), `hdg` (heading × 100) | `MAVLinkMessages.global_position_int()` |
| `ATTITUDE` | 20 Hz | `roll/pitch/yaw` (đổi từ độ sang radian), `rollspeed/pitchspeed/yawspeed` | `MAVLinkMessages.attitude()` |
| `GPS_RAW_INT` | 5 Hz | `fix_type`, `lat/lon` (degE7), `alt` (mm), `eph/epv` (từ `gps_hdop`/`gps_vdop` × 100), `vel` (tốc độ mặt đất cm/s), `cog` (course over ground), `satellites_visible` | `MAVLinkMessages.gps_raw_int()` + logic HDOP/VDOP/fix trong `send_gps()` |
| `BATTERY_STATUS` | 1 Hz | `voltages[10]` (giả lập pin 4S, chia đều điện áp), `current_battery` (cA, `-1` nếu không đo được), `battery_remaining` (%) | `send_battery()` |
| `SYS_STATUS` | 1 Hz | Bitmask sensor có mặt (`3D_GYRO`, `3D_ACCEL`, `3D_MAG`, `GPS`) cho cả 3 trường present/enabled/health, `voltage_battery`, `current_battery`, `battery_remaining` | `send_sys_status()` |
| `MISSION_CURRENT` | ≤5 Hz (chỉ khi mission đang active) | `seq` = waypoint hiện tại (0-based, quy đổi từ `current_waypoint` 1-based nội bộ) | `_send_mission_current()` |
| `MISSION_ITEM_REACHED` | theo sự kiện, ≤5 Hz check | `seq` waypoint vừa hoàn thành; có `mission_reached_seq` set để **không gửi lặp** cùng một seq | `_send_mission_item_reached()` |

- Debug: mỗi giây (`tx_debug_interval = 1.0`), `MAVLinkTelemetry.print_tx_status()` in ra console
  tổng số gói đã gửi theo từng loại (không gửi qua mạng, chỉ log nội bộ).

## 6. Nội dung điều khiển — chiều RX: Lệnh đơn (`CommandReceiver`)

Nhận diện theo `message.get_type()`, chỉ xử lý 4 loại message:

| MAVLink message | Xử lý |
|---|---|
| `COMMAND_LONG` | Dispatch theo `message.command` (xem bảng lệnh bên dưới) |
| `COMMAND_INT` | Dispatch theo `message.command`, chỉ hỗ trợ tập con: ARM/DISARM, TAKEOFF, LAND, RTL, MISSION_START |
| `SET_MODE` | Đọc `custom_mode` → map sang mode nội bộ |
| `SET_POSITION_TARGET_GLOBAL_INT` | Set điểm mục tiêu GUIDED (lat/lon từ `lat_int/lon_int` ÷ 1e7, alt từ `alt`) |

### Bảng `MAV_CMD` được hỗ trợ (qua `COMMAND_LONG`/`COMMAND_INT`)

| `MAV_CMD` | Giá trị số | Hành vi |
|---|---|---|
| `MAV_CMD_COMPONENT_ARM_DISARM` | 400 | `param1 >= 0.5` → `drone.arm()`, ngược lại `drone.disarm()` |
| `MAV_CMD_NAV_TAKEOFF` | 22 | Độ cao lấy từ `param7` (COMMAND_LONG) hoặc `z` (COMMAND_INT); nếu ≤0 dùng mặc định `10.0m`; gọi `drone.takeoff(altitude)` |
| `MAV_CMD_NAV_LAND` | 21 | `drone.land()` |
| `MAV_CMD_NAV_RETURN_TO_LAUNCH` | 20 | `drone.rtl()` |
| `MAV_CMD_MISSION_START` | 300 | `drone.start_mission()` |
| `MAV_CMD_DO_SET_MODE` | 176 | Chỉ với `COMMAND_LONG`: `param2` = custom_mode → map theo bảng mode bên dưới |

Mọi `command` không nằm trong danh sách trên: hàm trả `False`, **không gửi `COMMAND_ACK`** (khác
với `mavlink/server.py`, file đó có gửi `COMMAND_ACK` — nhưng như đã nói, không nằm trong luồng
runtime hiện tại).

### Bảng ánh xạ `custom_mode` (ArduPilot Copter) → hành vi simulator

| `custom_mode` | Tên ArduPilot | Hành vi trong simulator |
|---|---|---|
| 6 | RTL | Gọi `drone.rtl()` |
| 9 | LAND | Gọi `drone.land()` |
| 3 | AUTO | Gọi `drone.start_mission()` |
| 4 | GUIDED | `state.mode = "GUIDED"` |
| 5 | LOITER | `state.mode = "HOLD"`, `drone.set_speed(0.0)` |
| khác | — | Không hỗ trợ, trả `False` |

### `SET_POSITION_TARGET_GLOBAL_INT`

- Validate `lat` ∈ [-90, 90], `lon` ∈ [-180, 180].
- Gọi `drone.navigation.set_target(lat, lon, alt)`, tắt `rtl_active`, dừng `mission_navigator`,
  chuyển `state.mode = "GUIDED"`.

## 7. Nội dung điều khiển — chiều RX: Mission Protocol (`MissionReceiver`)

Cài đặt MAVLink Mission Protocol (upload/download/clear/set-current) theo mô hình
**staging trước khi commit**: mission cũ chỉ bị thay thế sau khi toàn bộ upload thành công.

### 7.1. Luồng UPLOAD (GCS → Simulator)

```
GCS                         Simulator
 |-- MISSION_COUNT(N) ------->|  staging_mission.clear(); upload_active=True
 |<-- MISSION_REQUEST_INT(0)--|
 |-- MISSION_ITEM_INT(seq=0)->|  lưu vào staging_mission nếu seq khớp expected_seq
 |<-- MISSION_REQUEST_INT(1)--|
 |-- MISSION_ITEM_INT(seq=1)->|
 |            ...             |
 |-- MISSION_ITEM_INT(N-1) -->|  received_count == expected_count
 |<-- MISSION_ACK(ACCEPTED) --|  commit: mission.clear() + copy từ staging_mission
```

- Hỗ trợ cả `MISSION_ITEM_INT` (khuyến nghị) lẫn `MISSION_ITEM` (legacy, tọa độ float thay vì
  int×1e7).
- **Lệnh waypoint được chấp nhận:** `MAV_CMD_NAV_WAYPOINT`, `MAV_CMD_NAV_TAKEOFF`,
  `MAV_CMD_NAV_LAND`. Lệnh khác → từ chối toàn bộ upload (`MAV_MISSION_UNSUPPORTED`).
- **Toạ độ:** `x`/`y` (hoặc `lat_int`/`lon_int` tuỳ field name trong dialect) ÷ 1e7 → độ; validate
  trong khoảng hợp lệ, sai → từ chối upload.
- **Độ cao (`_resolve_altitude`):** đọc theo `frame`:
  - `MAV_FRAME_GLOBAL_RELATIVE_ALT_INT` / `MAV_FRAME_GLOBAL_RELATIVE_ALT` → coi là độ cao tương
    đối (vì home altitude mô phỏng thường = 0m nên xử lý y hệt độ cao tuyệt đối trong code hiện
    tại).
  - `MAV_FRAME_GLOBAL_INT` / `MAV_FRAME_GLOBAL` → độ cao tuyệt đối.
  - Frame lạ → vẫn dùng `z` nhưng in cảnh báo log.
- **`param1`** của mission item = thời gian dừng tại waypoint (`hold_time`, giây, không âm).
- **Giới hạn an toàn:** `count > 1000` → từ chối ngay bằng `MAV_MISSION_ERROR` (chống upload bất
  thường).
- **Mất đồng bộ seq:** nếu `seq` nhận được ≠ `expected_seq`, simulator gửi lại
  `MISSION_REQUEST_INT(expected_seq)` để yêu cầu GCS gửi lại đúng thứ tự (không tự động phục hồi
  theo seq nhận được).
- Mission rỗng (`count = 0`): coi là hợp lệ, xoá mission hiện tại, trả `ACCEPTED` ngay.

### 7.2. Luồng DOWNLOAD (Simulator → GCS)

```
GCS                              Simulator
 |-- MISSION_REQUEST_LIST ------->|  download_active=True
 |<-- MISSION_COUNT(N) -----------|
 |-- MISSION_REQUEST_INT(seq) --->|  (hoặc MISSION_REQUEST legacy)
 |<-- MISSION_ITEM_INT(seq) ------|  frame=GLOBAL_RELATIVE_ALT_INT, cmd=NAV_WAYPOINT
 |            ...                 |
```

- Mỗi item trả về luôn build với `frame=MAV_FRAME_GLOBAL_RELATIVE_ALT_INT`,
  `command=MAV_CMD_NAV_WAYPOINT`, `current=0`, `autocontinue=1`, `param1=hold_time`,
  `param2..4=0`, toạ độ từ dữ liệu waypoint nội bộ (`waypoint.index = seq + 1`, 1-based).
- Hỗ trợ cả `mission_item_int_send` phiên bản dialect có/không có `mission_type` (thử/catch
  `TypeError` để tương thích nhiều bản `pymavlink`).

### 7.3. `MISSION_CLEAR_ALL`

Xoá cả `staging_mission` lẫn `mission` hiện tại, reset toàn bộ state upload/download, trả
`MISSION_ACK(ACCEPTED)`.

### 7.4. `MISSION_SET_CURRENT`

Set `mission.current_index = seq` (0-based) nếu waypoint tồn tại; không gửi ACK riêng cho message
này (không nằm trong đặc tả bắt buộc phải ACK).

### 7.5. Mã kết quả `MISSION_ACK` được dùng

| Hằng số | Khi nào |
|---|---|
| `MAV_MISSION_ACCEPTED` | Upload/clear thành công |
| `MAV_MISSION_ERROR` | `count` không parse được, hoặc `count > 1000` |
| `MAV_MISSION_UNSUPPORTED` | Item có `command` không thuộc tập hỗ trợ, hoặc toạ độ không parse được |

## 8. Message MAVLink còn lại chưa xử lý

Mọi message type không khớp danh sách ở mục 6–7 (ví dụ `PARAM_REQUEST_LIST`, `PARAM_SET`,
`RC_CHANNELS_OVERRIDE`, `HEARTBEAT` từ GCS, `TIMESYNC`, ...) bị `CommandReceiver.process()` và
`MissionReceiver.process()` cùng trả `False` một cách im lặng — **không log lỗi, không ACK, không
làm crash simulator**. Đây là hành vi "bỏ qua an toàn" theo thiết kế, không phải lỗi thiếu sót cần
sửa trừ khi có yêu cầu hỗ trợ thêm loại message cụ thể.

## 9. Tóm tắt sơ đồ luồng dữ liệu

```
                     UDP (một socket, RX+TX)
GCS  ───────────────────────────────────────────────────▶  MAVLinkConnection.receive()
(QGroundControl/                                                    │
 RIGEL GCS)                                                          ▼
                                                        parse_char() từng byte (pymavlink)
                                                                      │
                                                    ┌─────────────────┴─────────────────┐
                                                    ▼                                   ▼
                                          MissionReceiver.process()          CommandReceiver.process()
                                          (MISSION_*)                        (COMMAND_LONG/INT, SET_MODE,
                                                    │                         SET_POSITION_TARGET_GLOBAL_INT)
                                                    ▼                                   ▼
                                              drone.mission                        drone / FlightController
                                                    │                                   │
                                                    └─────────────────┬─────────────────┘
                                                                      ▼
                                                              Drone.update(dt)
                                                                      │
                                                                      ▼
                                                          MAVLinkTelemetry.update()
                                                     (HEARTBEAT, GLOBAL_POSITION_INT, ATTITUDE,
                                                      GPS_RAW_INT, BATTERY_STATUS, SYS_STATUS,
                                                      MISSION_CURRENT, MISSION_ITEM_REACHED)
                                                                      │
                                                                      ▼
                                                        MAVLinkConnection.send() ──▶ GCS (UDP)
```
