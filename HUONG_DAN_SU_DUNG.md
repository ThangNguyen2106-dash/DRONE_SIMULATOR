# Hướng dẫn sử dụng — MAVLink UAV Drone Simulator

Tài liệu này cung cấp hướng dẫn toàn diện và chi tiết về cách cài đặt, cấu hình, vận hành và kết nối **MAVLink UAV Drone Simulator** với các trạm mặt đất (GCS) như QGroundControl, Mission Planner hoặc các ứng dụng GCS tùy chỉnh.

---

## 1. Yêu cầu hệ thống & Chuẩn bị môi trường

- **Hệ điều hành**: Windows 10/11, macOS, Linux.
- **Python**: Phiên bản 3.9 trở lên (Khuyến nghị Python 3.10 hoặc 3.11).
- **Thư viện chính**:
  - `PySide6` (Qt6 UI Toolkit): Hiển thị đồ họa, giao diện người dùng và render 3D thời gian thực.
  - `pymavlink`: Thư viện xử lý đóng gói và giải mã khung bản tin chuẩn MAVLink.

---

## 2. Cài đặt & Khởi chạy

### Các bước cài đặt:

Mở cửa sổ dòng lệnh (Terminal hoặc PowerShell) tại thư mục gốc của dự án:

```powershell
# 1. Tạo môi trường ảo (khuyến nghị)
python -m venv .venv

# 2. Kích hoạt môi trường ảo
# Trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Trên Linux/macOS:
# source .venv/bin/activate

# 3. Nâng cấp pip và cài đặt gói phụ thuộc
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Khởi chạy phần mềm:

```powershell
python main.py
```

Khi khởi chạy, cửa sổ chính **MAVLINK UAV FLIGHT SIMULATOR** sẽ hiển thị với bố cục 2 cột trực quan:
- **Cột trái (3D Viewport)**: Khung nhìn 3D trực quan hóa chuyển động máy bay (60 FPS), hệ thống chỉ hướng la bàn HUD, tia Laser Neon và thanh trạng thái nhanh.
- **Cột phải (Control Panels)**: Khu vực các bảng cấu hình, điều khiển trực tiếp, cần lái ảo, danh sách nhiệm vụ và bảng Telemetry.

---

## 3. Tổng quan giao diện người dùng (GUI Layout)

Giao diện ứng dụng được chia thành các phân khu chức năng chuyên biệt:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      MAVLINK UAV FLIGHT SIMULATOR                      │
├──────────────────────────┬─────────────────────────────────────────────┤
│                          │  1. SIMULATION STATUS                       │
│                          ├─────────────────────────────────────────────┤
│                          │  2. DRONE CONFIGURATION                     │
│                          ├─────────────────────────────────────────────┤
│                          │  3. MAVLINK CONFIGURATION                   │
│      3D VIEWPORT         ├─────────────────────────────────────────────┤
│   - Drone Mesh 3D        │  4. LIVE SIMULATION CONTROL                 │
│   - Laser & Heading HUD  ├─────────────────────────────────────────────┤
│   - Ground Projection    │  5. VIRTUAL JOYSTICK & FLIGHT CONTROLS      │
│   - Quick Telemetry Bar  ├─────────────────────────────────────────────┤
│                          │  6. MISSION WAYPOINTS PANEL                 │
│                          ├─────────────────────────────────────────────┤
│                          │  7. LIVE TELEMETRY DISPLAY                  │
└──────────────────────────┴─────────────────────────────────────────────┘
```

---

## 4. Chi tiết các bảng điều khiển

### 4.1. Bảng Trạng thái mô phỏng (SIMULATION STATUS)
- **Status Indicator**: Hiển thị trạng thái của luồng mô phỏng (`STOPPED`, `STARTING...`, `RUNNING`, `ERROR`).
- **MAVLink Status**: Báo trạng thái socket mạng (`DISCONNECTED`, `CONNECTING...`, `CONNECTED`).
- **Nút START SIMULATION**: Khởi chạy luồng vật lý và mở socket MAVLink UDP.
- **Nút STOP SIMULATION**: Dừng mô phỏng, ngắt kết nối an toàn và khóa các bảng điều khiển.

---

### 4.2. Bảng Cấu hình tham số Drone (DRONE CONFIGURATION)
> **Lưu ý**: Các thông số này áp dụng khi nhấn nút **START SIMULATION**. Nếu thay đổi trong lúc đang chạy, giá trị sẽ được áp dụng cho phiên chạy kế tiếp.

| Tham số | Mô tả | Giá trị mặc định |
| :--- | :--- | :--- |
| **Latitude** | Vĩ độ ban đầu (Tọa độ Home) | `10.8231000` |
| **Longitude** | Kinh độ ban đầu (Tọa độ Home) | `106.6297000` |
| **Start Altitude** | Độ cao mặt đất ban đầu (m) | `0.0 m` |
| **Takeoff Altitude** | Độ cao mục tiêu mặc định khi cất cánh (m) | `20.0 m` |
| **Default Speed** | Tốc độ bay đường thẳng mặc định (m/s) | `5.0 m/s` |
| **Initial Heading** | Góc phương vị mũi ban đầu (0°–359.99°) | `90.0°` |

---

### 4.3. Bảng Cấu hình MAVLink UDP (MAVLINK CONFIGURATION)

| Tham số | Mô tả | Giá trị mặc định |
| :--- | :--- | :--- |
| **Connection Type** | Giao thức mạng kết nối | `UDP` |
| **IP Address** | Địa chỉ IP gửi dữ liệu Telemetry (TX Target) | `127.0.0.1` |
| **Port** | Cổng mạng UDP truyền nhận Telemetry | `14550` |
| **System ID** | MAVLink System ID của Drone giả lập | `1` |
| **Component ID** | MAVLink Component ID của Drone giả lập | `1` |
| **Telemetry Rate** | Tần số phát chuỗi bản tin định kỳ | `20.0 Hz` |

> Simulator hỗ trợ cơ chế **tự động học địa chỉ GCS**: Khi GCS gửi gói tin từ bất kỳ cổng nguồn nào tới cổng nhận của simulator (`14551`), simulator sẽ tự động phản hồi về đúng cổng đó.

---

### 4.4. Bảng Điều khiển trực tiếp (LIVE SIMULATION CONTROL)
> Bảng này được kích hoạt khi trạng thái là **RUNNING**. Mọi thay đổi áp dụng tức thì vào vòng lặp vật lý.

- **Flight Mode**: Chọn chế độ bay (`FREE`, `ALT_HOLD`, `MISSION`). Chế độ `MISSION` yêu cầu Drone đã ARM và có nạp sẵn Waypoint.
- **Altitude / Speed / Heading**: Thanh trượt kèm ô nhập số chính xác và nút **APPLY**.
- **Tọa độ tức thời (Latitude / Longitude)**: Cho phép dịch chuyển tọa độ máy bay tức thì cho mục đích kiểm thử.
- **Góc nghiêng Attitude (Roll / Pitch / Yaw)**: Can thiệp trực tiếp góc nghiêng động học.
- **Trạng thái Pin (Battery %)**: Thiết lập dung lượng pin giả lập để test cảnh báo pin yếu trên GCS.
- **Chất lượng GPS (GPS Fix / Satellites / HDOP / VDOP)**: Giả lập chất lượng định vị vệ tinh phục vụ kiểm tra an toàn bay.
- **Nút hành động nhanh**:
  - `ARM` / `DISARM`: Mở khóa / Khóa động cơ.
  - `TAKEOFF`: Tự động cất cánh lên độ cao thiết lập.
  - `LAND`: Hạ cánh thẳng đứng tại chỗ và tự động Disarm khi chạm đất.
  - `RTL`: Bay thẳng về tọa độ Home ban đầu và tự động hạ cánh.

---

### 4.5. Cần điều khiển ảo & Phím tắt bay (VIRTUAL JOYSTICK & KEYBOARD)
Hỗ trợ tương tác tay lái mượt mà với 3 phương thức:

1. **Cần Joystick ảo tương tác chuột (2D Virtual Joystick)**: Kéo thả chuột để điều khiển hướng tiến, lùi, rẽ trái, rẽ phải. Cần có cơ chế hồi tâm tự động khi thả chuột.
2. **Cụm D-Pad 8 hướng**: Nhấp nút định hướng để bay theo các hướng chính và góc chéo.
3. **Bàn phím phần cứng (Hardware Keyboard Control)**:

| Hướng bay | Phím WASD | Phím Numpad | Phím Mũi tên |
| :--- | :--- | :--- | :--- |
| **Tiến tới (Forward)** | `W` | `Num 8` | `↑` (Up) |
| **Lùi lại (Backward)** | `S` | `Num 2` | `↓` (Down) |
| **Tạt trái (Strafe Left)** | `A` | `Num 4` | `←` (Left) |
| **Tạt phải (Strafe Right)** | `D` | `Num 6` | `→` (Right) |
| **Bay chéo 4 góc** | `W+A`, `W+D`, `S+A`, `S+D` | `Num 7`, `Num 9`, `Num 1`, `Num 3` | Tổ hợp phím mũi tên |
| **Xoay đầu (Yaw)** | `Q` (Trái) / `E` (Phải) | — | — |
| **Độ cao (Altitude)** | `R` (Lên) / `F` (Xuống) | `Num +` / `Num -` | `PageUp` / `PageDown` |
| **Phanh dừng khẩn cấp** | `Space` (Phím cách) | `Num 5` | `Space` |

---

### 4.6. Bảng Quản lý nhiệm vụ (MISSION WAYPOINTS PANEL)
- **Bảng danh sách Waypoint**: Hiển thị thứ tự (Index), Hành động (`TAKEOFF`, `WAYPOINT`, `RTL`, `LAND`), Vĩ độ, Kinh độ, Độ cao, Tốc độ và Thời gian dừng (`Hold Time`).
- **Thêm Waypoint thủ công**: Nhập tọa độ và nhấn **ADD WAYPOINT**.
- **Chèn bước RTL (Bay về nhà)**: Nhấn **ADD RTL** để chèn điểm quay về Home vào giữa hoặc cuối chu trình nhiệm vụ.
- **Điều chỉnh tốc độ chung**: Nhập tốc độ và nhấn **APPLY ALL SPEEDS** để cập nhật nhanh cho toàn bộ lộ trình.
- **Xóa nhiệm vụ**: Nhấn **CLEAR ALL** để đặt lại danh sách nhiệm vụ.
- **Đồng bộ hai chiều với GCS**: Khi GCS nạp nhiệm vụ qua MAVLink, bảng này tự động cập nhật và làm nổi bật điểm Waypoint đang bay tới theo thời gian thực.

---

### 4.7. Bảng Dữ liệu bay thời gian thực (LIVE TELEMETRY)
Cập nhật dữ liệu động học với tần số 100 Hz:
- **Flight State**: Flight Mode, Armed status, Battery %.
- **Position & Motion**: GPS Latitude, Longitude, Altitude, Ground Speed, Heading.
- **Attitude**: Roll, Pitch, Yaw.
- **Mission Progress**: Current Waypoint index (`x / N`), Khoảng cách tới điểm đích (`Distance`), Sai số độ cao (`Altitude Error`).

---

## 5. Hướng dẫn kết nối với Phần mềm Trạm Mặt Đất (GCS)

### 5.1. Kết nối với QGroundControl (QGC)

1. Mở **QGroundControl**.
2. Nhấn vào biểu tượng **QGC Logo (Góc trên trái) → Application Settings → Comm Links**.
3. Nhấn **Add** để tạo đường truyền mới:
   - **Name**: `UAV Simulator Link`
   - **Type**: `UDP`
   - **Listening Port**: `14550`
   - **Server Addresses (Tùy chọn)**: `127.0.0.1:14551`
4. Chọn kết nối vừa tạo và nhấn **Connect**.
5. QGroundControl sẽ nhận diện máy bay ngay khi bạn nhấn **START SIMULATION** trên phần mềm mô phỏng.

---

### 5.2. Kết nối với Mission Planner

1. Mở **Mission Planner**.
2. Tại góc trên bên phải, chọn loại kết nối là **UDP**.
3. Nhấn **Connect**.
4. Khi hộp thoại hiện ra hỏi cổng lắng nghe, nhập: `14550` rồi nhấn **OK**.
5. Mission Planner sẽ tự động tải các thông số và hiển thị Drone trên bản đồ vệ tinh.

---

## 6. Các tính năng bay nâng cao & Cơ chế an toàn

### 6.1. Khóa đầu và đường cong giảm tốc mượt mà (Deceleration Profile)
Khi bay tự động theo Waypoint, Drone liên tục hướng mũi về tọa độ đích và tự động giảm tốc êm ái khi tiếp cận tâm bán kính chấp nhận:
$$v(d) = v_{\max} \cdot \sqrt{\frac{d}{d_{\text{decel}}}}$$
Điều này ngăn chặn triệt để hiện tượng văng trớn (overshoot) hoặc giật khựng khi chuyển tiếp giữa các điểm.

### 6.2. Can thiệp né vật cản trong lúc chạy Mission (Obstacle Avoidance Nudge)
Trong quá trình Drone đang tự động bay Mission hoặc đang bay RTL, người điều khiển có thể lập tức can thiệp bằng bàn phím hoặc cần Joystick ảo để né chướng ngại vật:
- Tín hiệu can thiệp sẽ dạt hướng máy bay sang một bên.
- Khi người lái nhả tay điều khiển, Drone sẽ tự động tiếp tục hành trình về Waypoint hiện tại mà không làm mất tiến trình nhiệm vụ.

### 6.3. Tự động ngắt Arm khi chạm đất (Auto-Disarm on Touchdown)
Khi thực hiện lệnh **LAND** hoặc kết thúc chu trình **RTL**:
- Drone tự động hạ độ cao với vận tốc an toàn.
- Ngay khi độ cao đạt $0.0\,\text{m}$ (chạm đất), trạng thái chuyển sang **DISARMED**, động cơ tắt hoàn toàn và bàn điều khiển tự động khóa an toàn.

---

## 7. Xử lý sự cố thường gặp (Troubleshooting FAQ)

| Hiện tượng | Nguyên nhân | Hướng khắc phục |
| :--- | :--- | :--- |
| **Báo lỗi `ModuleNotFoundError: PySide6`** | Chưa cài đặt thư viện giao diện Qt6 | Chạy lệnh `pip install PySide6` trong môi trường ảo |
| **Nhấn START báo trạng thái `ERROR`** | Cổng UDP `14550` hoặc `14551` đang bị ứng dụng khác chiếm giữ | Đóng các phần mềm GCS hoặc đổi số hiệu cổng trong panel MAVLINK CONFIGURATION |
| **GCS không nhận được tín hiệu Heartbeat** | Cấu hình sai cổng lắng nghe trên GCS | Đảm bảo GCS lắng nghe ở cổng `14550` và simulator đang ở trạng thái `RUNNING` |
| **Lệnh điều khiển từ GCS không phản hồi** | GCS gửi tới sai cổng nhận của Drone | Đảm bảo cổng gửi lệnh của GCS là `14551` |
| **Không chọn được chế độ `MISSION`** | Drone chưa được ARM hoặc danh sách Waypoint đang rỗng | Nhấn **ARM** trước, sau đó nạp Waypoint rồi mới chuyển chế độ sang **MISSION** |
| **Con lăn chuột tự làm nhảy số trên ô nhập liệu** | Cuộn chuột vô tình trúng ô SpinBox | Ứng dụng đã tích hợp bộ lọc chặn cuộn chuột trên toàn bộ ô số để đảm bảo an toàn tuyệt đối |
