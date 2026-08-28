# Hướng dẫn sử dụng — RIGEL UAV Drone Simulator

Tài liệu này hướng dẫn chi tiết cách cài đặt, cấu hình và vận hành simulator, dựa trên giao diện
và mã nguồn hiện tại của ứng dụng (`main.py`, `gui/*`, `config/simulator.json`).

## 1. Yêu cầu

- Python 3.9+ (đã build/test với 3.11).
- Các gói: `pymavlink` (trong `requirements.txt`) và `PySide6` (cài thêm thủ công, xem bước 2).
- Windows / PowerShell (các lệnh dưới đây dùng cú pháp PowerShell).

## 2. Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
pip install PySide6
```

> `requirements.txt` hiện chỉ liệt kê `pymavlink`. Nếu chưa cài `PySide6`, ứng dụng sẽ báo lỗi
> `ModuleNotFoundError: No module named 'PySide6'` khi chạy `main.py`.

## 3. Chạy ứng dụng

```powershell
python main.py
```

Cửa sổ **RIGEL UAV SIMULATOR** sẽ mở ra với 3 phần chính, từ trên xuống dưới:

1. **DRONE SIMULATOR** — trạng thái, telemetry rút gọn, nút START/STOP.
2. **DRONE CONFIGURATION** — tham số ban đầu của drone.
3. **MAVLINK CONFIGURATION** — tham số kết nối MAVLink.
4. Dòng trạng thái **MAVLink: DISCONNECTED / CONNECTED** ở cuối cửa sổ.

## 4. Cấu hình trước khi chạy

Các panel cấu hình chỉ chỉnh được **khi simulator đang STOPPED** (bị khoá khi đang RUNNING).

### 4.1. DRONE CONFIGURATION

| Trường | Ý nghĩa | Mặc định |
|---|---|---|
| Latitude | Vĩ độ điểm xuất phát (home) | `10.8231000` |
| Longitude | Kinh độ điểm xuất phát (home) | `106.6297000` |
| Start Altitude | Độ cao ban đầu (m), lúc drone chưa cất cánh | `0.0` |
| Takeoff Altitude | Độ cao mục tiêu khi lệnh TAKEOFF được thực hiện (m) | `20.0` |
| Speed | Tốc độ bay mặc định (m/s) | `5.0` |
| Heading | Hướng bay mặc định (độ, 0–359.99°) | `90.0` |

### 4.2. MAVLINK CONFIGURATION

| Trường | Ý nghĩa | Mặc định |
|---|---|---|
| Connection Type | Loại kết nối (hiện chỉ hỗ trợ `UDP`) | `UDP` |
| IP Address | Địa chỉ IP đích để gửi telemetry (TX) | `127.0.0.1` |
| Port | Cổng UDP dùng để gửi/nhận | `14550` |
| System ID | MAVLink system ID của drone giả lập | `1` |
| Component ID | MAVLink component ID | `1` |
| Telemetry Rate | Tần suất gửi telemetry (Hz) | `20.0 Hz` |

> Cấu hình mặc định của cổng RX (nhận lệnh từ GCS) nằm ở `config/simulator.json`
> (`rx_port: 14551`), không chỉnh trực tiếp từ giao diện.

## 5. Bắt đầu / dừng mô phỏng

1. Kiểm tra lại **DRONE CONFIGURATION** và **MAVLINK CONFIGURATION**.
2. Bấm **START**:
   - Trạng thái chuyển `STARTING...` → `RUNNING` khi worker khởi động xong.
   - Dòng MAVLink chuyển `CONNECTING...` → `CONNECTED`.
   - Hai panel cấu hình bị khoá (disable) trong lúc chạy.
   - Khu vực telemetry rút gọn hiển thị `ALT / SPD / BAT` cập nhật liên tục.
3. Bấm **STOP** để dừng:
   - Trạng thái chuyển `STOPPING...` → `STOPPED`.
   - MAVLink chuyển về `DISCONNECTED`, telemetry rút gọn về `--`.
   - Hai panel cấu hình được mở khoá lại để chỉnh cho lần chạy tiếp theo.
4. Nếu có lỗi khi kết nối/chạy (ví dụ cổng đang bị chiếm), trạng thái sẽ hiển thị `ERROR` và dòng
   MAVLink hiển thị nội dung lỗi; simulator tự dừng worker.
5. Đóng cửa sổ ứng dụng cũng sẽ tự động dừng worker đang chạy (nếu có) trước khi thoát.

## 6. Kết nối GCS (QGroundControl / RIGEL GCS)

Với cấu hình mặc định:

- Simulator **gửi** telemetry tới `127.0.0.1:14550` (TX).
- Simulator **nhận** lệnh điều khiển / mission tại `0.0.0.0:14551` (RX).

Cách kết nối QGroundControl:

1. Vào **Application Settings → Comm Links**, tạo một **UDP Link** lắng nghe ở cổng `14550`.
2. Kết nối link. QGroundControl sẽ thấy heartbeat và telemetry từ simulator gần như ngay lập tức
   nếu simulator đang **RUNNING**.
3. Các lệnh QGC gửi đi (ARM, TAKEOFF, đổi mode, upload mission, ...) sẽ được gửi tới cổng RX
   (`14551`) và được `mavlink/command_receiver.py` / `mavlink/mission_receiver.py` xử lý.

Nếu đổi `Port` trong MAVLINK CONFIGURATION, cổng TX sẽ đổi theo giá trị đó — nhớ cập nhật lại UDP
Link trong GCS cho khớp.

## 7. Debug UDP (không cần GCS)

`test_udp.py` là script độc lập, lắng nghe cổng RX mặc định (`14551`) và in ra dữ liệu nhận được —
hữu ích để kiểm tra xem có dữ liệu thực sự gửi tới simulator hay không, mà không cần mở GCS.

```powershell
python test_udp.py
```

Chạy song song với `main.py` (đã START) và gửi lệnh từ GCS/công cụ khác để quan sát log.

## 8. Ghi chú về các panel chưa gắn vào giao diện chính

Trong mã nguồn có sẵn hai widget bổ sung nhưng **hiện chưa được gắn vào `MainWindow`**
(`gui/main_window.py` chỉ dựng `DroneConfigPanel` và `MAVLinkConfigPanel`):

- `gui/manual_control_panel.py` — `ManualControlPanel`: các nút ARM / DISARM / TAKEOFF / LAND / RTL
  để điều khiển thủ công không cần GCS.
- `gui/failure_panel.py` — `FailurePanel`: bật/tắt lỗi GPS / Compass / RC Link / EKF và chỉnh gió
  (tốc độ + hướng) trong lúc mô phỏng đang chạy.

Hai panel này đã có đầy đủ logic UI và callback hook (`on_arm`, `on_gps_failure`, ...) nhưng cần
được `MainWindow` khởi tạo, thêm vào layout và nối callback tới `SimulationWorker` /
`FlightController` thì mới xuất hiện và hoạt động được trên giao diện. Nếu cần dùng ngay, có thể
gọi trực tiếp các phương thức tương ứng trên `simulator/drone.py` / `simulator/flight_controller.py`
từ code, hoặc chờ tích hợp vào `MainWindow`.

## 9. Sự cố thường gặp

| Hiện tượng | Nguyên nhân khả dĩ | Cách xử lý |
|---|---|---|
| `ModuleNotFoundError: PySide6` | Chưa cài PySide6 | `pip install PySide6` |
| Trạng thái chuyển ngay sang `ERROR` khi START | Cổng UDP đang bị chương trình khác chiếm | Đổi `Port` trong MAVLINK CONFIGURATION hoặc đóng ứng dụng đang dùng cổng đó |
| GCS không thấy heartbeat | Sai cổng UDP Link trong GCS, hoặc simulator chưa STARTED | Kiểm tra lại cổng trùng với `Port` cấu hình, đảm bảo trạng thái là `RUNNING` |
| Lệnh từ GCS không có tác dụng | GCS gửi tới sai cổng RX | Mặc định RX là `14551` (`config/simulator.json`), kiểm tra bằng `test_udp.py` |
