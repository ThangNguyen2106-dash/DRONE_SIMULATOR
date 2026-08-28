# RIGEL UAV Drone Simulator

Trình mô phỏng drone (UAV) MAVLink, có giao diện đồ họa (PySide6), dùng để giả lập một máy bay không người lái gửi telemetry và nhận lệnh điều khiển qua **MAVLink UDP**, tương thích với QGroundControl hoặc RIGEL GCS. Đây là công cụ phục vụ việc phát triển/kiểm thử phần mềm mặt đất (GCS) mà không cần drone hoặc phần cứng thật.

Giao tiếp MAVLink sử dụng UDP socket thuần (`socket` chuẩn của Python) thay vì `mavutil.mavlink_connection()`, việc encode/decode message dựa trên `pymavlink`.

## Kiến trúc

```
main.py                    Điểm khởi chạy ứng dụng GUI (PySide6)

core/
  state.py                 DroneState - trạng thái bay dùng chung (có lock để thread-safe)
  navigation.py             Tính khoảng cách/bearing/sai số độ cao tới điểm mục tiêu

simulation/
  flight_model.py           Mô hình vật lý bay đơn giản (tốc độ, hướng, độ cao, gia tốc...)

simulator/
  drone.py                  Lớp Drone: state machine chính (ARM, TAKEOFF, LAND, RTL,
                             MISSION, ALT_HOLD, set vị trí/hướng/tốc độ/pin/GPS...)
  flight_controller.py      Cầu nối giữa lệnh MAVLink và Drone
  mission.py                 Quản lý danh sách waypoint (thêm/xóa/duyệt mission)
  mission_navigator.py      Điều hướng drone bám theo mission đã nạp

mavlink/
  connection.py              Kết nối MAVLink (mở/đóng, gửi/nhận)
  server.py                   UDP server thuần dùng raw socket + pymavlink encoder
                               (heartbeat, telemetry, xử lý COMMAND_LONG...)
  telemetry.py                Sinh và gửi các bản tin telemetry định kỳ
  command_receiver.py         Nhận và xử lý lệnh điều khiển từ GCS
  mission_receiver.py         Nhận mission (danh sách waypoint) upload từ GCS
  messages.py                  Định nghĩa/tiện ích cho các MAVLink message

gui/
  main_window.py              Cửa sổ chính: nút START/STOP, hiển thị trạng thái & telemetry
  drone_config_panel.py       Cấu hình vị trí ban đầu, độ cao takeoff, tốc độ, hướng bay
  mavlink_config_panel.py     Cấu hình kết nối MAVLink (IP, port, system/component ID, tần suất telemetry)
  manual_control_panel.py     Điều khiển bay thủ công: ARM/DISARM/TAKEOFF/LAND/RTL
  failure_panel.py            Giả lập lỗi (GPS/Compass/RC/EKF) và gió, áp dụng ngay khi đang chạy
  simulation_worker.py        QThread chạy vòng lặp mô phỏng, tách khỏi luồng GUI

config/
  simulator.json               File cấu hình mặc định (system/component ID, cổng, tần suất, vị trí home)

test_udp.py                    Script debug: lắng nghe UDP RX để kiểm tra dữ liệu gửi tới simulator
```

## Tính năng chính

- **Telemetry MAVLink** đầy đủ: heartbeat, system time, global/local position, attitude, VFR HUD,
  GPS raw, system status, battery, IMU, distance sensor, RC channels, nav controller output,
  extended system state (tùy theo dialect pymavlink đã cài).
- **Điều khiển bay**: ARM, DISARM, TAKEOFF, LAND, RTL, đổi flight mode (FREE / MISSION / ALT_HOLD),
  set tốc độ, hướng bay (heading), vị trí (lat/lon/alt), attitude (roll/pitch/yaw), mức pin.
- **Mission**: nhận danh sách waypoint từ GCS (upload mission chuẩn MAVLink), tự động bay bám theo
  waypoint, tính khoảng cách/hướng còn lại, phát hiện hoàn thành mission.
- **Giả lập lỗi (fault injection)**: bật/tắt lỗi GPS, Compass, RC link, EKF và gió (tốc độ + hướng)
  ngay trong lúc mô phỏng đang chạy, để kiểm tra khả năng phản ứng của GCS.
- **Giao diện đồ họa**: cấu hình drone/MAVLink trước khi chạy, theo dõi trạng thái & telemetry
  (độ cao, tốc độ, pin) theo thời gian thực, điều khiển thủ công không cần GCS.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
pip install PySide6
python main.py
```

> **Lưu ý:** `requirements.txt` hiện chỉ liệt kê `pymavlink`. Ứng dụng GUI còn cần `PySide6`
> (`from PySide6.QtWidgets import QApplication`) nên cần cài thêm thủ công như trên, hoặc bổ sung
> `PySide6` vào `requirements.txt`.

## Cách sử dụng

1. Chạy `python main.py` để mở giao diện.
2. Ở panel **DRONE CONFIGURATION**: chỉnh vị trí xuất phát (lat/lon), độ cao ban đầu, độ cao takeoff,
   tốc độ và hướng bay mặc định.
3. Ở panel **MAVLINK CONFIGURATION**: chỉnh IP/port, System ID, Component ID, tần suất gửi telemetry
   (mặc định UDP).
4. Bấm **START** để khởi động mô phỏng (simulator sẽ mở UDP TX/RX và bắt đầu gửi heartbeat/telemetry).
5. Kết nối QGroundControl / RIGEL GCS tới cổng UDP tương ứng, hoặc dùng panel **MANUAL FLIGHT CONTROL**
   để điều khiển trực tiếp (ARM/DISARM/TAKEOFF/LAND/RTL) mà không cần GCS.
6. Dùng panel **FAILURE SIMULATION & WIND** để bật lỗi hoặc chỉnh gió trong lúc bay, quan sát phản ứng
   trên GCS.
7. Bấm **STOP** để dừng mô phỏng và đóng kết nối.

## Cổng mặc định (config/simulator.json)

- TX `127.0.0.1:14550`: simulator → GCS (telemetry, heartbeat)
- RX `0.0.0.0:14551`: GCS → simulator (lệnh điều khiển, mission)
- Telemetry rate: 20 Hz
- Home mặc định: lat `10.8231`, lon `106.6297`, alt `0.0`

## Kết nối QGroundControl

Tạo một UDP Link lắng nghe ở cổng `14550`. Simulator sẽ gửi telemetry tới `127.0.0.1:14550`.

## Debug UDP

`test_udp.py` là script độc lập để lắng nghe cổng UDP RX (`14551`) và in ra dữ liệu nhận được,
hữu ích khi cần kiểm tra xem GCS có thực sự gửi lệnh tới simulator hay không.

```powershell
python test_udp.py
```
