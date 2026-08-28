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
  main_window.py              Cửa sổ chính: START/STOP, panel DRONE/MAVLINK CONFIGURATION, khối
                               LIVE SIMULATION CONTROL (mode, slider, ARM/DISARM/TAKEOFF/LAND/RTL,
                               GPS override) và LIVE TELEMETRY, chạy điều khiển trực tiếp qua
                               SimulationWorker.queue_command()
  drone_config_panel.py       Cấu hình vị trí ban đầu, độ cao takeoff, tốc độ, hướng bay
  mavlink_config_panel.py     Cấu hình kết nối MAVLink (IP, port, system/component ID, tần suất telemetry)
  manual_control_panel.py     (chưa dùng) Widget ARM/DISARM/TAKEOFF/LAND/RTL độc lập, không được
                               main_window.py import — chức năng tương đương đã có sẵn trực tiếp
                               trong LIVE SIMULATION CONTROL
  failure_panel.py            (chưa dùng) Widget giả lập lỗi GPS/Compass/RC/EKF + gió, không được
                               main_window.py import — hiện chưa có đường bật từ giao diện
  simulation_worker.py        QThread chạy vòng lặp mô phỏng + hàng đợi lệnh runtime, tách khỏi
                               luồng GUI

config/
  simulator.json               File cấu hình tham khảo (system/component ID, cổng, tần suất, vị trí
                                home); không được GUI đọc trực tiếp khi khởi động
```

## Tính năng chính

- **Telemetry MAVLink** đầy đủ: heartbeat, system time, global/local position, attitude, VFR HUD,
  GPS raw, system status, battery, IMU, distance sensor, RC channels, nav controller output,
  extended system state (tùy theo dialect pymavlink đã cài).
- **Điều khiển bay**: ARM, DISARM, TAKEOFF, LAND, RTL, đổi flight mode (FREE / MISSION / ALT_HOLD),
  set tốc độ, hướng bay (heading), vị trí (lat/lon/alt), attitude (roll/pitch/yaw), mức pin.
- **Mission**: nhận danh sách waypoint từ GCS (upload mission chuẩn MAVLink), tự động bay bám theo
  waypoint, tính khoảng cách/hướng còn lại, phát hiện hoàn thành mission.
- **Giao diện đồ họa**: cấu hình drone/MAVLink trước khi chạy; khi đang chạy có khối **LIVE
  SIMULATION CONTROL** để điều khiển trực tiếp (mode, altitude/speed/heading, lat/lon, roll/pitch/
  yaw, battery, GPS fix/satellites/HDOP/VDOP, ARM/DISARM/TAKEOFF/LAND/RTL) mà không cần GCS, cùng
  khối **LIVE TELEMETRY** theo dõi trạng thái theo thời gian thực.

> **Ghi chú:** repo có sẵn `gui/failure_panel.py` (giả lập lỗi GPS/Compass/RC/EKF + gió) và
> `gui/manual_control_panel.py`, nhưng **chưa được `gui/main_window.py` sử dụng** — xem
> `HUONG_DAN_SU_DUNG.md` mục 6 để biết chi tiết.

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
5. Kết nối QGroundControl / RIGEL GCS tới cổng UDP tương ứng, hoặc dùng khối **LIVE SIMULATION
   CONTROL** để điều khiển trực tiếp (mode, altitude/speed/heading, lat/lon, roll/pitch/yaw,
   battery, GPS, ARM/DISARM/TAKEOFF/LAND/RTL) mà không cần GCS.
6. Theo dõi khối **LIVE TELEMETRY** để xem trạng thái bay cập nhật theo thời gian thực.
7. Bấm **STOP** để dừng mô phỏng và đóng kết nối.

Chi tiết từng điều khiển, xem `HUONG_DAN_SU_DUNG.md`.

## Cổng mặc định (config/simulator.json)

- TX `127.0.0.1:14550`: simulator → GCS (telemetry, heartbeat)
- RX `0.0.0.0:14551`: GCS → simulator (lệnh điều khiển, mission)
- Telemetry rate: 20 Hz
- Home mặc định: lat `10.8231`, lon `106.6297`, alt `0.0`

## Kết nối QGroundControl

Tạo một UDP Link lắng nghe ở cổng `14550`. Simulator sẽ gửi telemetry tới `127.0.0.1:14550`.

## Tài liệu chi tiết

- `HUONG_DAN_SU_DUNG.md` — hướng dẫn từng bước sử dụng giao diện.
- `GIAO_THUC_MAVLINK.md` — chi tiết giao thức MAVLink (transport, framing, telemetry, lệnh điều
  khiển, mission protocol).
