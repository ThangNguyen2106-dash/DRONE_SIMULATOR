# Hướng dẫn sử dụng — RIGEL UAV Drone Simulator

Tài liệu này hướng dẫn chi tiết cách cài đặt, cấu hình và vận hành simulator, dựa trên giao diện
và mã nguồn hiện tại của ứng dụng (`main.py`, `gui/main_window.py`, `gui/drone_config_panel.py`,
`gui/mavlink_config_panel.py`, `gui/mission_panel.py`, `simulator/drone.py`,
`mavlink/mission_receiver.py`, `config/simulator.json`).

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
(`QScrollArea`), gồm các khối chính từ trên xuống dưới:

1. **Thanh trạng thái** (luôn cố định trên đầu) — trạng thái mô phỏng, đèn/nhãn MAVLink, đèn/nhãn
   ARM-DISARM, nút START/STOP.
2. **DRONE CONFIGURATION** — tham số ban đầu của drone (chỉ áp dụng lúc khởi động).
3. **MAVLINK CONFIGURATION** — tham số kết nối MAVLink.
4. **LIVE SIMULATION CONTROL** — điều khiển trực tiếp drone khi đang chạy (mode, slider,
   ARM/DISARM/TAKEOFF/LAND/RTL, GPS...). Bị khoá (disable) cho tới khi simulator ở trạng thái
   RUNNING.
5. **MISSION WAYPOINTS** — soạn/nạp/chạy mission nhiều waypoint, đồng bộ hai chiều với GCS ngoài.
6. **JOYSTICK** — hai cần điều khiển ảo để bay tay ở chế độ FREE.
7. **LIVE TELEMETRY** — bảng telemetry chi tiết cập nhật liên tục theo thời gian thực.

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
   - Trạng thái chuyển `Status: STARTING...` → `Status: RUNNING` (worker phát tín hiệu `READY`
     hoặc `RUNNING` đều được UI hiển thị là `RUNNING`).
   - Dòng MAVLink chuyển `CONNECTING...` → `CONNECTED` (đèn tròn xanh).
   - Đèn ARM/DISARM sáng **đỏ** với nhãn `DISARMED` — drone luôn khởi động ở trạng thái chưa arm.
   - Khối **LIVE SIMULATION CONTROL** và **MISSION WAYPOINTS** được mở khoá (enable).
   - Khối **LIVE TELEMETRY** bắt đầu cập nhật liên tục.
3. Bấm **STOP** để dừng:
   - Trạng thái chuyển `Status: STOPPING...` → `Status: STOPPED`.
   - MAVLink chuyển về `DISCONNECTED`, đèn ARM/DISARM reset về đỏ/`DISARMED`.
   - **LIVE SIMULATION CONTROL** và **MISSION WAYPOINTS** bị khoá lại.
4. Nếu có lỗi khi kết nối/chạy (ví dụ cổng đang bị chiếm), trạng thái hiển thị `Status: ERROR`,
   dòng MAVLink hiển thị nội dung lỗi, các khối điều khiển bị khoá, nút START mở lại để thử START
   lần nữa.
5. Đóng cửa sổ ứng dụng cũng sẽ tự động dừng worker đang chạy (nếu có) trước khi thoát.

## 6. ARM / DISARM — điều kiện bắt buộc để điều khiển bay

Đèn tròn trên thanh trạng thái (cạnh đèn MAVLink) luôn phản ánh trạng thái arm hiện tại của
drone theo thời gian thực:

- 🔴 **đỏ + `DISARMED`** — drone chưa arm.
- 🟢 **xanh + `ARMED`** — drone đã arm, sẵn sàng nhận lệnh bay.

**Quy tắc:** mọi thao tác điều khiển bay đều bị chặn khi drone chưa ARM — kể cả khi gửi qua
MAVLink GUIDED (Mission Planner/QGroundControl), không chỉ riêng thao tác trong GUI:

- Nút **TAKEOFF / LAND / RTL**.
- Nút **START MISSION**.
- Kéo slider hoặc bấm **APPLY** ở Altitude / Speed / Heading.
- Bấm **APPLY** ở Latitude / Longitude.
- Kéo joystick.

Nếu thử bất kỳ thao tác nào ở trên khi chưa ARM, ứng dụng hiện hộp thoại cảnh báo **"Chưa ARM"**
nhắc bấm ARM trước (joystick và slider chỉ cảnh báo một lần cho tới khi trạng thái arm thay đổi,
tránh spam hộp thoại liên tục khi kéo).

Ngược lại, bấm **DISARM** khi drone **đang bay có độ cao** (> 0.05 m) cũng bị chặn kèm cảnh báo
— phải LAND hoặc RTL cho drone chạm đất trước khi disarm được.

> Khi drone hạ cánh xong từ lệnh **LAND** hoặc **RTL** (chạm đất, độ cao về 0), hệ thống **tự động
> DISARM** — muốn bay tiếp phải bấm ARM lại từ đầu, giống hành vi của autopilot thật.

Mỗi khi bấm một nút hành động, ô **Status** trên thanh trạng thái cũng hiện tạm thời tên hành
động đang thực hiện, ví dụ: `Status: ARMING...`, `Status: TAKEOFF...`, `Status: RETURN TO
HOME...`, `Status: LANDING...`, `Status: HOME POSITION SET`.

## 7. Điều khiển trực tiếp — LIVE SIMULATION CONTROL

Khối này chỉ dùng được khi simulator đang **RUNNING**. Toàn bộ thay đổi được gửi tới
`SimulationWorker` qua hàng đợi lệnh runtime (`queue_command`) và áp dụng ngay trong vòng lặp mô
phỏng, không cần dừng/khởi động lại. Xem mục 6 để biết những thao tác nào yêu cầu ARM trước.

| Điều khiển | Kiểu | Hành vi |
|---|---|---|
| Flight Mode | Combo box: `FREE` / `ALT_HOLD` / `MISSION` | Đổi ngay khi chọn. `MISSION` yêu cầu drone đã ARM và đã có mission nạp sẵn, nếu không sẽ bị từ chối âm thầm (mode không đổi) |
| Altitude | Spin box + slider (0–1000 m) + nút **APPLY** | Kéo slider/spin đồng bộ hai chiều; yêu cầu đã ARM (xem mục 6) |
| Speed | Spin box + slider (0–100 m/s) + nút **APPLY** | Tương tự Altitude, yêu cầu đã ARM |
| Heading | Spin box + slider (0–360°) + nút **APPLY** | Tương tự Altitude, yêu cầu đã ARM |
| Latitude / Longitude | Spin box + nút **APPLY** riêng từng trường | Dịch chuyển tức thời vị trí drone, yêu cầu đã ARM |
| Roll / Pitch / Yaw | Spin box, gửi lệnh **ngay khi thay đổi giá trị** (không cần nút Apply) | Đặt góc attitude giả lập — dùng cho debug/test, không yêu cầu ARM |
| Battery | Spin box (0–100%) + nút **APPLY** | Ép mức pin — dùng cho debug/test, không yêu cầu ARM |
| GPS Fix / Satellites / HDOP / VDOP | Spin box + nút **APPLY GPS** (một nút áp dụng cả 4 giá trị cùng lúc) | Giả lập chất lượng GPS gửi trong `GPS_RAW_INT` — không yêu cầu ARM |
| ARM / DISARM / TAKEOFF / LAND / RTL / SET HOME = HERE | Nút bấm | TAKEOFF dùng giá trị hiện tại của ô **Altitude** làm độ cao mục tiêu. DISARM bị chặn nếu drone đang bay (xem mục 6) |

> Các ô Altitude/Speed/Heading/Latitude/Longitude/Roll/Pitch/Yaw/Battery/GPS Fix/Satellites/HDOP/
> VDOP cũng **tự đồng bộ ngược** theo telemetry thực tế mỗi khi có dữ liệu mới từ `Drone`, để phản
> ánh đúng trạng thái bay hiện tại (ví dụ trong lúc TAKEOFF/LAND tự động, ô Altitude sẽ tự chạy
> theo `target_altitude`).

> **Lưu ý:** repo còn hai file `gui/manual_control_panel.py` (`ManualControlPanel`) và
> `gui/failure_panel.py` (`FailurePanel`, giả lập lỗi GPS/Compass/RC/EKF + gió) nhưng **không được
> `gui/main_window.py` import/sử dụng** — chức năng ARM/DISARM/TAKEOFF/LAND/RTL hiện đã có sẵn
> ngay trong khối LIVE SIMULATION CONTROL mô tả ở trên bằng cách khác; riêng tính năng giả lập lỗi
> GPS/Compass/RC/EKF và gió trong `FailurePanel` **hiện chưa có đường nào để bật từ giao diện**.

## 8. Bay tay — JOYSTICK

Hai cần ảo (trái/phải) chỉ dùng được khi drone đã **ARM** (xem mục 6):

- **Cần trái**: X = tốc độ xoay yaw, Y = tốc độ lên/xuống.
- **Cần phải**: X = nghiêng trái/phải (dịch ngang thân), Y = nghiêng tiến/lùi.

Nếu đang chạy **MISSION** hoặc **RTL**, joystick không thay thế hoàn toàn autopilot — chỉ cộng
thêm một "nudge" nhỏ lên trên tốc độ đang bay tự động (dùng để né chướng ngại vật mà không huỷ
mission/RTL đang chạy).

## 9. Bay theo hành trình — MISSION WAYPOINTS

### 9.1. Quy trình cơ bản

1. Nhập **Latitude / Longitude / Altitude / Speed** rồi bấm **ADD WAYPOINT** (lặp lại cho từng
   điểm). Có thể bấm **ADD RTL (bay về nhà)** để thêm một bước "quay về home" vào cuối hành trình.
2. Có thể sửa trực tiếp trong bảng (double-click hoặc phím Edit) các ô Latitude/Longitude/
   Altitude/Speed; **REMOVE SELECTED** xoá dòng đang chọn.
3. **CLEAR ALL** xoá toàn bộ mission — thao tác này xoá cả bảng hiển thị lẫn mission thật trên
   drone, sau đó bảng vẫn tiếp tục đồng bộ bình thường với các mission upload sau này (kể cả từ
   GCS ngoài).
4. (Tuỳ chọn) Đặt **Tốc độ chung mission (m/s)** rồi bấm **ÁP DỤNG TỐC ĐỘ** để set tốc độ mặc
   định cho các waypoint tiếp theo được thêm.
5. Bấm **UPLOAD TO DRONE** để đẩy toàn bộ bảng xuống mission thật của drone.
6. **ARM** drone (mục 6), sau đó bấm **START MISSION** để bắt đầu bay tự động; **STOP MISSION**
   để dừng giữa chừng.

### 9.2. Đồng bộ hai chiều với GCS ngoài

Bảng mission tự động đồng bộ theo mission thật trên drone mỗi tick — nên waypoint upload từ
**Mission Planner** hay **QGroundControl** qua MAVLink cũng hiển thị ngay trong bảng, kể cả khi
mission đang bay (tiến độ waypoint hiện tại cập nhật theo thời gian thực ở cột **Trạng thái**).
Khi đang có chỉnh sửa cục bộ chưa **UPLOAD TO DRONE**, việc đồng bộ tạm dừng để không mất thao
tác đang dở, và tiếp tục lại ngay sau khi UPLOAD hoặc CLEAR ALL.

### 9.3. Các loại mission item được hỗ trợ

Simulator chấp nhận đầy đủ các lệnh mission phổ biến của Mission Planner/QGroundControl:

- **Điều hướng thật** (tạo waypoint bay được): `WAYPOINT`, `SPLINE_WAYPOINT`, `TAKEOFF`, `LAND`,
  `RETURN_TO_LAUNCH`, `LOITER_UNLIM`, `LOITER_TURNS`, `LOITER_TIME`, `DELAY`/`CONDITION_DELAY`.
- **DELAY**: hiển thị đúng thời gian chờ (giây) ở cột Speed; khi bay tới điểm delay, drone đứng
  yên tại chỗ cho đủ thời gian rồi mới bay tiếp — không còn hiện tượng lượn vòng tại chỗ.
- **Lệnh phụ trợ** (`DO_*`/`CONDITION_*` như camera, servo, ROI, fence, jump, parachute...):
  không có mô hình vật lý tương ứng trong simulator, nhưng được **chấp nhận (ACK)** thay vì làm
  toàn bộ mission upload thất bại với lỗi `MAV_MISSION_UNSUPPORTED`.

### 9.4. Quy tắc bay RTL (Return To Launch)

Khi kích hoạt RTL (nút RTL trong LIVE SIMULATION CONTROL, hoặc bước RTL trong mission):

1. Drone giữ nguyên độ cao hiện tại và bay ngang về home, **giảm tốc dần** khi còn cách home
   khoảng 15 m (thay vì bay full tốc độ rồi phanh gấp).
2. Khi đã tới đúng vị trí home theo phương ngang, drone mới bắt đầu **hạ độ cao thẳng về 0 m**.
3. Chạm đất xong, drone **tự động DISARM** — bay lại phải ARM lại từ đầu (xem mục 6).

## 10. Theo dõi — LIVE TELEMETRY

Bảng hiển thị dạng lưới 2 cột, cập nhật theo mỗi lần `SimulationWorker` phát tín hiệu
`telemetry_updated` (tần số nội bộ ~100 Hz, giới hạn bởi `time.sleep(0.01)` trong vòng lặp
worker):

Mode · Armed · Latitude · Longitude · Altitude · Speed · Heading · Roll · Pitch · Yaw · Battery ·
Current WP (dạng `x / N`, chỉ hiện khi có mission) · Distance (khoảng cách tới mục tiêu hiện tại)
· Altitude Error (sai số so với độ cao mục tiêu).

## 11. Kết nối GCS (Mission Planner / QGroundControl)

Với cấu hình mặc định:

- Simulator **gửi** telemetry tới `127.0.0.1:14550` (TX).
- Simulator **nhận** lệnh điều khiển / mission tại `0.0.0.0:14551` (RX).

Cách kết nối QGroundControl (tương tự với Mission Planner, chỉ khác tên menu):

1. Vào **Application Settings → Comm Links**, tạo một **UDP Link** lắng nghe ở cổng `14550`.
2. Kết nối link. QGroundControl/Mission Planner sẽ thấy heartbeat và telemetry từ simulator gần
   như ngay lập tức nếu simulator đang **RUNNING**.
3. Các lệnh GCS gửi đi (ARM, TAKEOFF, đổi mode, upload mission, ...) sẽ được gửi tới cổng RX
   (`14551`) và được `mavlink/command_receiver.py` / `mavlink/mission_receiver.py` xử lý.
4. Mission upload từ GCS phải tuân theo quy tắc ARM ở mục 6 giống hệt điều khiển từ GUI — nếu
   GCS gửi lệnh AUTO/GUIDED trong khi drone chưa arm, lệnh sẽ bị từ chối ở tầng mô phỏng.

Nếu đổi `Port` trong MAVLINK CONFIGURATION, cổng TX sẽ đổi theo giá trị đó — nhớ cập nhật lại UDP
Link trong GCS cho khớp.

## 12. Sự cố thường gặp

| Hiện tượng | Nguyên nhân khả dĩ | Cách xử lý |
|---|---|---|
| `ModuleNotFoundError: PySide6` | Chưa cài PySide6 | `pip install PySide6` |
| Trạng thái chuyển ngay sang `ERROR` khi START | Cổng UDP đang bị chương trình khác chiếm | Đổi `Port` trong MAVLINK CONFIGURATION hoặc đóng ứng dụng đang dùng cổng đó |
| GCS không thấy heartbeat | Sai cổng UDP Link trong GCS, hoặc simulator chưa STARTED | Kiểm tra lại cổng trùng với `Port` cấu hình, đảm bảo trạng thái là `RUNNING` |
| Lệnh từ GCS không có tác dụng | GCS gửi tới sai cổng RX, hoặc drone chưa ARM | Mặc định RX là `14551` (`config/simulator.json`); ARM drone trước khi gửi lệnh bay |
| Nút trong LIVE SIMULATION CONTROL bị mờ, không bấm được | Simulator chưa ở trạng thái RUNNING | Bấm START và đợi trạng thái chuyển sang RUNNING |
| Bấm TAKEOFF/RTL/kéo slider/joystick hiện hộp thoại "Chưa ARM" | Drone chưa ARM | Bấm ARM trước khi thao tác (xem mục 6) |
| Không DISARM được | Drone đang bay có độ cao | LAND hoặc RTL cho drone chạm đất trước, hệ thống sẽ tự disarm |
| Đổi Flight Mode sang MISSION không có tác dụng | Drone chưa ARM hoặc chưa có mission nào được nạp | ARM trước, và nạp mission (qua GUI hoặc GCS) trước khi chọn MISSION |
| Upload mission từ Mission Planner báo `MAV_MISSION_UNSUPPORTED` | Mission item dùng lệnh MAV_CMD chưa được hỗ trợ | Xem danh sách lệnh hỗ trợ ở mục 9.3; báo lại nếu vẫn gặp lệnh bị từ chối |
| Bấm CLEAR ALL xong không nhận mission mới nữa | Đã sửa ở bản hiện tại — nếu vẫn gặp, cập nhật code lên bản mới nhất | `git pull` nhánh đang dùng |
