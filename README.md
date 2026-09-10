# MAVLink UAV Drone Simulator

> **Trình mô phỏng thiết bị bay không người lái (UAV Quadcopter) 3D thời gian thực chuẩn giao thức MAVLink UDP**, tích hợp mô hình khí động học 6 bậc tự do (6-DOF), điều hướng đa hướng 8 trục, hiển thị đồ họa 3D hiện đại và hỗ trợ kết nối trực tiếp hai chiều với **QGroundControl**, **Mission Planner** hoặc bất kỳ phần mềm trạm mặt đất (GCS) tương thích MAVLink.

---

## 🌟 Giới thiệu tổng quan

**MAVLink UAV Drone Simulator** là phần mềm giả lập máy bay không người lái 4 cánh quạt (Quadcopter) hoàn chỉnh, được xây dựng trên nền tảng **Python** kết hợp giao diện đồ họa **PySide6 (Qt6)** và tầng giao tiếp mạng **MAVLink (UDP Socket)**. 

Phần mềm được thiết kế nhằm phục vụ kỹ sư điều khiển, lập trình viên nhúng và nhóm phát triển phần mềm trạm mặt đất (GCS) có thể:
- Kiểm thử thuật toán bay tự động, điều hướng bám điểm tọa độ (Waypoint Navigation) và bay tuần tra nhiệm vụ (Mission).
- Phát triển và kiểm thử phần mềm GCS (QGroundControl, Mission Planner, Custom Web/Desktop GCS) hoàn toàn độc lập mà không cần kết nối phần cứng máy bay thật.
- Giả lập động học bay 6-DOF thực tế, phản hồi trực quan qua khung nhìn 3D thời gian thực và dòng dữ liệu Telemetry liên tục.

---

## ✨ Tính năng nổi bật

### 1. Không gian hiển thị 3D thời gian thực (60 FPS)
- **Mô hình 3D Mesh chi tiết cao**: Khung carbon fiber siêu nhẹ, cụm camera gimbal 4K, 4 động cơ không chổi than (Brushless Motors), cánh quạt xoay động lực học theo tốc độ vòng tua và chân đáp hạ cánh.
- **Hệ thống nhận diện hướng mũi trực quan (Forward Heading System)**:
  - **Tia Laser Neon 3D & Mũi tên dẫn hướng**: Vươn dài từ mũi Drone với nhãn hiển thị `MŨI TRƯỚC (FWD)`.
  - **Đèn pha rọi trước & Tam giác dạ quang**: Cụm đèn pha chiếu sáng phía trước kết hợp tam giác định hướng trên lưng máy bay.
  - **Hình chiếu mặt đất & La bàn chiến thuật HUD**: Mũi tên định vị hướng la bàn chiếu trực tiếp trên mặt đất và đồng hồ la bàn điện tử xoay thời gian thực ở góc màn hình.
- **Mô phỏng ánh sáng động (Dynamic 3D Shading)**: Đổ bóng mặt đất, hiệu ứng phản xạ thấu kính, đèn LED hàng hải (Xanh phải / Đỏ trái) nhấp nháy chân thực.

### 2. Mô hình động lực học bay đa hướng 8 trục (6-DOF Omnidirectional Physics)
- **Chuyển động đa hướng độc lập (Holonomic Motion)**: Drone có khả năng tiến, lùi, tạt ngang trái/phải và bay chéo 4 góc tự do mà không phụ thuộc vào góc xoay của mũi máy bay.
- **Góc nghiêng khí động học chuẩn xác (Realistic Aerodynamic Tilts)**:
  - **Bay tiến (Forward)**: Chúi mũi xuống phía trước ($\text{Pitch} < 0$).
  - **Bay lùi / Hãm phanh (Backward / Braking)**: Ngửa mũi lên ($\text{Pitch} > 0$) để triệt tiêu vận tốc.
  - **Tạt cánh (Roll)**: Nghiêng cánh chúc xuống theo hướng tạt trái/phải.

### 3. Thuật toán điều hướng Waypoint & Can thiệp né vật cản
- **Khóa góc mũi liên tục về Waypoint (Continuous Heading Lock)**: Mũi Drone luôn tự động xoay và hướng thẳng về điểm Waypoint đang hoạt động.
- **Tiếp cận & Giảm tốc chính xác (Precision Deceleration Profile)**: Tự động giảm tốc êm ái khi đến gần tâm tọa độ theo hàm căn bậc hai $\sqrt{d / d_{decel}}$, tránh tình trạng giật cục hay văng trớn.
- **Tự động lùi/dạt ngang tìm tọa độ (Không lượn vòng)**: Nếu bay quá trớn tọa độ (Overshoot), Drone tự động dùng lực đẩy lùi và dạt ngang để kéo máy bay về đúng tâm tọa độ mà không cần quay đầu lượn vòng cung.
- **Can thiệp lái né vật cản trong lúc chạy Mission (Obstacle Avoidance Nudge)**: Phi công có thể can thiệp tay lái (WASD / Joystick / Numpad) để lách né chướng ngại vật ngay khi đang bay Mission tự động hoặc RTL mà không làm hủy tiến trình nhiệm vụ.

### 4. Hỗ trợ toàn diện chu trình Nhiệm vụ (Mission Protocol)
- Tích hợp chuẩn **MAVLink Mission Protocol**: Hỗ trợ nạp (Upload), đọc (Download), xóa (Clear) và kích hoạt nhiệm vụ bay từ GCS hoặc từ bảng điều khiển nhiệm vụ tích hợp trong simulator.
- Hỗ trợ các lệnh điều hướng & hành động:
  - `MAV_CMD_NAV_TAKEOFF`: Tự động cất cánh đạt độ cao thiết lập.
  - `MAV_CMD_NAV_WAYPOINT`: Bay đến tọa độ đích và giữ vị trí theo thời gian chờ (`hold_time`).
  - `MAV_CMD_NAV_LOITER_TIME`: Bay đến vị trí và lượn treo cố định vị trí theo thời gian.
  - `MAV_CMD_NAV_RETURN_TO_LAUNCH (RTL)`: Bay về tọa độ Home ban đầu.
  - `MAV_CMD_NAV_LAND`: Tự động hạ cánh từ từ chạm đất.
  - `MAV_CMD_DO_CHANGE_SPEED`: Thay đổi tốc độ bay trên hành trình.

### 5. Tự động Tắt Arm & Khóa an toàn khi hạ cánh (Auto-Disarm on Landing)
- Khi thực hiện lệnh **Return to Home (RTL)** hoặc **LAND**, Drone tự động bay về điểm xuất phát và hạ cánh thẳng đứng về độ cao `0.0m`.
- Ngay khi chạm đất, hệ thống **tự động Tắt Arm (`DISARMED`)**, ngừng quay cánh quạt và **khóa toàn bộ can thiệp điều khiển** để đảm bảo an toàn tuyệt đối.

### 6. Tương thích toàn diện chuẩn MAVLink UDP
- Giao tiếp qua giao thức mạng UDP thuần socket, hỗ trợ toàn bộ các bản tin MAVLink chuẩn:
  - `HEARTBEAT`, `SYS_STATUS`, `SYSTEM_TIME`, `GPS_RAW_INT`, `GLOBAL_POSITION_INT`, `ATTITUDE`, `VFR_HUD`, `RC_CHANNELS`, `MISSION_ITEM_REACHED`, `MISSION_CURRENT`, `COMMAND_ACK`.
- Nhận lệnh và upload/download nhiệm vụ tự động hoàn toàn tương thích với **QGroundControl**, **Mission Planner** và các **Custom GCS**.

---

## 🎮 Bảng phím tắt điều khiển bay (Keyboard Flight Controls)

Bạn có thể điều khiển trực tiếp máy bay bằng **WASD**, **Bàn phím số Numpad (8-2-4-6)** hoặc **Phím mũi tên**:

| Thao tác bay | Phím WASD | Phím Numpad | Phím Mũi tên | Chức năng động học |
| :--- | :--- | :--- | :--- | :--- |
| **Tiến tới (Forward)** | `W` | `Num 8` | `↑` (Up Arrow) | Chúi mũi và tăng tốc tiến về phía trước |
| **Lùi lại (Backward)** | `S` | `Num 2` | `↓` (Down Arrow) | Ngửa mũi phanh/lùi về phía sau |
| **Tạt Trái (Strafe Left)** | `A` | `Num 4` | `←` (Left Arrow) | Nghiêng cánh và dạt sang trái |
| **Tạt Phải (Strafe Right)** | `D` | `Num 6` | `→` (Right Arrow) | Nghiêng cánh và dạt sang phải |
| **Bay chéo 4 góc** | `W+A`, `W+D`, `S+A`, `S+D` | `Num 7`, `Num 9`, `Num 1`, `Num 3` | `↑+←`, `↑+→`, `↓+←`, `↓+→` | Bay chéo 8 hướng mượt mà |
| **Xoay đầu (Yaw)** | `Q` (Trái) / `E` (Phải) | — | — | Xoay góc phương vị đầu Drone |
| **Độ cao (Altitude)** | `R` (Lên) / `F` (Xuống) | `Num +` / `Num -` | `PageUp` / `PageDown` | Nâng / hạ độ cao bay |
| **Phanh dừng khẩn cấp** | `Space` (Phím cách) | `Num 5` | `Space` | Phanh gấp và giữ vị trí đứng yên (Hover) |

---

## 📁 Cấu trúc thư mục dự án

```
DRONE_SIMULATOR/
├── main.py                     # Entry point khởi động ứng dụng GUI
├── requirements.txt            # Danh sách thư viện phụ thuộc (PySide6, pymavlink)
├── LICENSE                     # Giấy phép sử dụng phần mềm
├── README.md                   # Tài liệu giới thiệu tổng quan dự án
├── HUONG_DAN_SU_DUNG.md        # Cẩm nang hướng dẫn sử dụng và vận hành chi tiết
├── GIAO_THUC_MAVLINK.md        # Đặc tả kỹ thuật triển khai giao thức MAVLink UDP
├── MISSION_ACTIONS_V02.md      # Tài liệu đặc tả các lệnh hành động nhiệm vụ
├── MISSION_WRITE_AND_FLIGHT.md # Hướng dẫn luồng nạp và thực thi Mission
├── config/
│   └── simulator.json          # Cấu hình tham số mặc định (Tọa độ Home, cổng UDP, tần số...)
├── core/
│   ├── state.py                # DroneState - Trạng thái động học dùng chung (Thread-safe lock)
│   └── navigation.py           # Tính toán khoảng cách Haversine, bearing và tọa độ GPS
├── gui/
│   ├── main_window.py          # Cửa sổ chính giao diện điều khiển và telemetry
│   ├── drone_3d_widget.py      # Widget hiển thị mô hình 3D Drone 60FPS với bóng đổ và chỉ hướng
│   ├── joystick_panel.py       # Cần điều khiển Joystick ảo, D-Pad 8 hướng và bộ bắt phím
│   ├── drone_config_panel.py   # Panel cấu hình tọa độ ban đầu, tốc độ và độ cao
│   ├── mavlink_config_panel.py # Panel cấu hình cổng MAVLink UDP và tần số truyền tin
│   ├── mission_panel.py        # Panel theo dõi và quản lý nhiệm vụ bay tự động
│   └── simulation_worker.py    # QThread xử lý vòng lặp vật lý và hàng đợi lệnh độc lập
├── mavlink/
│   ├── connection.py           # Quản lý socket UDP gửi/nhận MAVLink
│   ├── server.py               # MAVLink Server xử lý định kỳ Telemetry và Heartbeat
│   ├── telemetry.py            # Đóng gói và gửi các bản tin MAVLink Telemetry
│   ├── command_receiver.py     # Nhận và thực thi lệnh COMMAND_LONG, MANUAL_CONTROL từ GCS
│   └── mission_receiver.py     # Xử lý giao thức nạp/rút Waypoint Mission từ GCS
└── simulation/
    └── flight_model.py         # Mô hình vật lý bay 6-DOF, quán tính, gia tốc và góc nghiêng
```

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy

### 1. Yêu cầu hệ thống
- Hệ điều hành: Windows 10/11, macOS, hoặc Linux
- Python phiên bản **3.9** trở lên (Khuyến nghị 3.10 hoặc 3.11)

### 2. Cài đặt môi trường

Mở Terminal hoặc PowerShell tại thư mục dự án:

```powershell
# 1. Tạo môi trường ảo (khuyến nghị)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Nâng cấp pip và cài đặt thư viện
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Khởi chạy ứng dụng

```powershell
python main.py
```

---

## 📖 Quy trình vận hành cơ bản

1. **Cấu hình thông số ban đầu**:
   - Tại panel **DRONE CONFIGURATION**: Kiểm tra tọa độ Home xuất phát (mặc định: `10.823100, 106.629700`), độ cao cất cánh mong muốn và tốc độ bay.
   - Tại panel **MAVLINK CONFIGURATION**: Cấu hình cổng UDP truyền nhận (Mặc định TX: `127.0.0.1:14550`, RX: `0.0.0.0:14551`).
2. **Bắt đầu mô phỏng**:
   - Nhấn nút **START SIMULATION** trên thanh điều khiển.
   - Đèn trạng thái chuyển sang xanh (`RUNNING`), báo hiệu hệ thống đã sẵn sàng phát tín hiệu Heartbeat và Telemetry.
3. **Cất cánh và điều khiển**:
   - Nhấn **ARM** để mở khóa động cơ.
   - Nhấn **TAKEOFF** để máy bay tự động cất cánh lên độ cao đã định.
   - Sử dụng bàn phím (`W/A/S/D`, Numpad hoặc Mũi tên) hoặc cần Joystick ảo để điều khiển bay tự do.
4. **Chạy nhiệm vụ tự động (Mission)**:
   - Nạp danh sách Waypoint từ trạm mặt đất (QGroundControl / Mission Planner) hoặc thêm trực tiếp trên panel **MISSION WAYPOINTS**.
   - Chuyển chế độ sang **MISSION** (hoặc gửi lệnh `AUTO` từ GCS).
   - Drone sẽ tự động bay bám theo lộ trình, khóa đầu về hướng điểm đến và tự động thực hiện các hành động tại từng điểm.
5. **Hạ cánh & Dừng mô phỏng**:
   - Nhấn **RTL** hoặc **LAND** để Drone tự động bay về điểm xuất phát và hạ cánh.
   - Khi chạm đất tại độ cao `0.0m`, máy bay sẽ tự động **Tắt Arm (`DISARMED`)**.
   - Nhấn **STOP SIMULATION** để đóng kết nối mô phỏng an toàn.

---

## 📡 Cấu hình kết nối Trạm Mặt Đất (GCS)

- **QGroundControl / Mission Planner / Custom GCS**:
  - **Loại kết nối**: UDP Link
  - **Cổng lắng nghe (Listening Port / GCS Port)**: `14550` (Simulator gửi Telemetry tới cổng này)
  - **Cổng gửi lệnh (Target Port / Drone Port)**: `14551` (GCS gửi lệnh điều khiển tới cổng này)
  - **Địa chỉ IP**: `127.0.0.1` (Localhost khi chạy cùng máy) hoặc IP LAN của máy chạy Simulator.

---

## 📚 Tài liệu chi tiết liên quan

- [Hướng dẫn sử dụng chi tiết (User Manual)](HUONG_DAN_SU_DUNG.md)
- [Đặc tả kỹ thuật Giao thức MAVLink UDP](GIAO_THUC_MAVLINK.md)
- [Quy trình nạp và thực thi Mission](MISSION_WRITE_AND_FLIGHT.md)
- [Danh mục lệnh nhiệm vụ Mission Actions V02](MISSION_ACTIONS_V02.md)
