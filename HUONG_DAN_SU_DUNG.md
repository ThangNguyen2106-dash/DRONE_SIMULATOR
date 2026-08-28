# Hướng dẫn sử dụng — RIGEL UAV Drone Simulator

Tài liệu này hướng dẫn chi tiết cách cài đặt, cấu hình và vận hành simulator, dựa trên giao diện
và mã nguồn hiện tại của ứng dụng (`main.py`, `gui/main_window.py`, `gui/drone_config_panel.py`,
`gui/mavlink_config_panel.py`, `config/simulator.json`).

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

Cửa sổ **RIGEL UAV SIMULATOR** (kích thước tối thiểu 1200×850) mở ra với nội dung có thể cuộn
(`QScrollArea`), gồm 5 khối chính từ trên xuống dưới:

1. **SIMULATION STATUS** — trạng thái, dòng MAVLink, nút START/STOP.
2. **DRONE CONFIGURATION** — tham số ban đầu của drone (chỉ áp dụng lúc khởi động).
3. **MAVLINK CONFIGURATION** — tham số kết nối MAVLink.
4. **LIVE SIMULATION CONTROL** — điều khiển trực tiếp drone khi đang chạy (mode, slider,
   ARM/DISARM/TAKEOFF/LAND/RTL, GPS...). Bị khoá (disable) cho tới khi simulator ở trạng thái
   RUNNING.
5. **LIVE TELEMETRY** — bảng telemetry chi tiết cập nhật liên tục theo thời gian thực.

## 4. Cấu hình trước khi chạy

Hai panel **DRONE CONFIGURATION** và **MAVLINK CONFIGURATION** chỉ có tác dụng cho lần bấm
**START** tiếp theo — chúng không bị khoá khi simulator đang chạy, nhưng chỉnh sửa lúc đó không
ảnh hưởng tới phiên đang chạy (giá trị chỉ được đọc một lần lúc `start_simulation()`).

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
   - Trạng thái chuyển `STARTING...` → `RUNNING` (worker phát tín hiệu `READY` hoặc `RUNNING` đều
     được UI hiển thị là `RUNNING`).
   - Dòng MAVLink chuyển `CONNECTING...` → `CONNECTED`.
   - Khối **LIVE SIMULATION CONTROL** được mở khoá (enable) để điều khiển trực tiếp.
   - Khối **LIVE TELEMETRY** bắt đầu cập nhật liên tục.
3. Bấm **STOP** để dừng:
   - Trạng thái chuyển `STOPPING...` → `STOPPED`.
   - MAVLink chuyển về `DISCONNECTED`.
   - **LIVE SIMULATION CONTROL** bị khoá lại.
4. Nếu có lỗi khi kết nối/chạy (ví dụ cổng đang bị chiếm), trạng thái hiển thị `ERROR`, dòng
   MAVLink hiển thị nội dung lỗi, **LIVE SIMULATION CONTROL** bị khoá, nút START mở lại để thử
   START lần nữa.
5. Đóng cửa sổ ứng dụng cũng sẽ tự động dừng worker đang chạy (nếu có) trước khi thoát.

## 6. Điều khiển trực tiếp — LIVE SIMULATION CONTROL

Khối này chỉ dùng được khi simulator đang **RUNNING**. Toàn bộ thay đổi được gửi tới
`SimulationWorker` qua hàng đợi lệnh runtime (`queue_command`) và áp dụng ngay trong vòng lặp mô
phỏng, không cần dừng/khởi động lại.

| Điều khiển | Kiểu | Hành vi |
|---|---|---|
| Flight Mode | Combo box: `FREE` / `ALT_HOLD` / `MISSION` | Đổi ngay khi chọn. `MISSION` yêu cầu drone đã ARM và đã có mission nạp sẵn, nếu không sẽ bị từ chối âm thầm (mode không đổi) |
| Altitude | Spin box + slider (0–1000 m) + nút **APPLY** | Kéo slider/spin đồng bộ hai chiều; giá trị chỉ gửi lệnh khi kéo slider hoặc bấm APPLY |
| Speed | Spin box + slider (0–100 m/s) + nút **APPLY** | Tương tự Altitude |
| Heading | Spin box + slider (0–360°) + nút **APPLY** | Tương tự Altitude |
| Latitude / Longitude | Spin box + nút **APPLY** riêng từng trường | Dịch chuyển tức thời vị trí drone |
| Roll / Pitch / Yaw | Spin box, gửi lệnh **ngay khi thay đổi giá trị** (không cần nút Apply) | Đặt góc attitude giả lập |
| Battery | Spin box (0–100%) + nút **APPLY** | Ép mức pin |
| GPS Fix / Satellites / HDOP / VDOP | Spin box + nút **APPLY GPS** (một nút áp dụng cả 4 giá trị cùng lúc) | Giả lập chất lượng GPS gửi trong `GPS_RAW_INT` |
| ARM / DISARM / TAKEOFF / LAND / RTL | Nút bấm | TAKEOFF dùng giá trị hiện tại của ô **Altitude** làm độ cao mục tiêu |

> Các ô Altitude/Speed/Heading/Latitude/Longitude/Roll/Pitch/Yaw/Battery/GPS Fix/Satellites/HDOP/
> VDOP cũng **tự đồng bộ ngược** theo telemetry thực tế mỗi khi có dữ liệu mới từ `Drone`, để phản
> ánh đúng trạng thái bay hiện tại (ví dụ trong lúc TAKEOFF/LAND tự động, ô Altitude sẽ tự chạy
> theo `target_altitude`).

> **Lưu ý:** repo còn hai file `gui/manual_control_panel.py` (`ManualControlPanel`) và
> `gui/failure_panel.py` (`FailurePanel`, giả lập lỗi GPS/Compass/RC/EKF + gió) nhưng **không được
> `gui/main_window.py` import/sử dụng** — chức năng ARM/DISARM/TAKEOFF/LAND/RTL hiện đã có sẵn
> ngay trong khối LIVE SIMULATION CONTROL mô tả ở trên bằng cách khác; riêng tính năng giả lập lỗi
> GPS/Compass/RC/EKF và gió trong `FailurePanel` **hiện chưa có đường nào để bật từ giao diện**.

## 7. Theo dõi — LIVE TELEMETRY

Bảng hiển thị dạng lưới 2 cột, cập nhật theo mỗi lần `SimulationWorker` phát tín hiệu
`telemetry_updated` (tần số nội bộ ~100 Hz, giới hạn bởi `time.sleep(0.01)` trong vòng lặp
worker):

Mode · Armed · Latitude · Longitude · Altitude · Speed · Heading · Roll · Pitch · Yaw · Battery ·
Current WP (dạng `x / N`, chỉ hiện khi có mission) · Distance (khoảng cách tới mục tiêu hiện tại)
· Altitude Error (sai số so với độ cao mục tiêu).

## 8. Kết nối GCS (QGroundControl / RIGEL GCS)

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

## 9. Sự cố thường gặp

| Hiện tượng | Nguyên nhân khả dĩ | Cách xử lý |
|---|---|---|
| `ModuleNotFoundError: PySide6` | Chưa cài PySide6 | `pip install PySide6` |
| Trạng thái chuyển ngay sang `ERROR` khi START | Cổng UDP đang bị chương trình khác chiếm | Đổi `Port` trong MAVLINK CONFIGURATION hoặc đóng ứng dụng đang dùng cổng đó |
| GCS không thấy heartbeat | Sai cổng UDP Link trong GCS, hoặc simulator chưa STARTED | Kiểm tra lại cổng trùng với `Port` cấu hình, đảm bảo trạng thái là `RUNNING` |
| Lệnh từ GCS không có tác dụng | GCS gửi tới sai cổng RX | Mặc định RX là `14551` (`config/simulator.json`) |
| Nút trong LIVE SIMULATION CONTROL bị mờ, không bấm được | Simulator chưa ở trạng thái RUNNING | Bấm START và đợi trạng thái chuyển sang RUNNING |
| Đổi Flight Mode sang MISSION không có tác dụng | Drone chưa ARM hoặc chưa có mission nào được nạp | ARM trước, và nạp mission qua GCS (upload mission MAVLink) trước khi chọn MISSION |
