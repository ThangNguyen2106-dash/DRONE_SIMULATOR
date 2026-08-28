# Ghi chú chỉnh sửa Mission — 2026-08-28

Tài liệu này liệt kê các thay đổi đã thực hiện trong phiên làm việc hôm nay,
kèm lý do phát sinh và giải pháp áp dụng.

---

## 1. Hỗ trợ mục RTL (bay về nhà) trong mission

**Lý do:**
Trước đây, mission chỉ hỗ trợ 3 loại lệnh: `MAV_CMD_NAV_WAYPOINT`,
`MAV_CMD_NAV_TAKEOFF`, `MAV_CMD_NAV_LAND`. Khi người dùng muốn mission có
bước "bay về home rồi bay tiếp waypoint khác" (ví dụ: bay tới điểm A, quay
về nhà, rồi bay tiếp tới điểm B), hệ thống không có cách nào biểu diễn được
hành động này trong danh sách waypoint.

**Giải pháp:**
- `simulator/mission.py`: thêm trường `action: str = "waypoint"` vào
  dataclass `Waypoint` (giá trị có thể là `"waypoint"`, `"takeoff"`,
  `"land"`, `"rtl"`).
- `mavlink/mission_receiver.py`:
  - Thêm `MAV_CMD_NAV_RETURN_TO_LAUNCH` vào danh sách lệnh được chấp nhận
    khi nhận mission từ GCS (Mission Planner / QGroundControl), ở cả hai
    hàm xử lý `_store_mission_item_int` (MISSION_ITEM_INT) và
    `_store_mission_item_legacy` (MISSION_ITEM cũ).
  - Vì GCS thường gửi tọa độ `x=y=z=0` cho mục RTL (ý nghĩa là "về vị trí
    home", không phải tọa độ (0,0)), thêm hàm `_resolve_home()` để lấy
    tọa độ home thật của drone (qua callback `get_home_position`) thay vì
    dùng tọa độ 0,0 nhận được từ message.
  - Khi tải mission xuống lại cho GCS (`_send_mission_item_int`,
    `_send_mission_item`), trả đúng lệnh `MAV_CMD_NAV_RETURN_TO_LAUNCH`
    nếu waypoint có `action == "rtl"`, thay vì luôn trả về
    `MAV_CMD_NAV_WAYPOINT`.
- `gui/simulation_worker.py`: hàm tạo `MissionReceiver` được truyền thêm
  `get_home_position=self.drone.get_home_position` để nó biết tọa độ home;
  xử lý `action == "rtl"` khi thêm waypoint runtime qua lệnh
  `add_waypoint`.
- `gui/mission_panel.py`: thêm nút **"ADD RTL (bay về nhà)"** để người
  dùng tự chèn bước RTL vào giữa mission ngay trên GUI, không cần GCS.

**Vì sao dùng cách này:**
`MissionNavigator` (bộ điều hướng mission) vốn đã coi mỗi waypoint chỉ là
một điểm tọa độ để bay tới rồi tiếp tục — không cần biết ý nghĩa của điểm
đó. Vì vậy cách đơn giản và ít rủi ro nhất là: khi gặp RTL, chỉ cần tạo
một "waypoint" có tọa độ = home, gắn nhãn `action="rtl"` để hiển thị/xuất
lại đúng, mà không cần sửa logic điều hướng.

**Bug phát sinh trong lúc sửa và đã fix kèm:**
Khi hoàn tất upload mission (`_finish_upload`), code copy từng waypoint
từ `staging_mission` sang `mission` chính thức nhưng quên truyền
`action=waypoint.action`, khiến RTL bị "quên" thành waypoint thường sau
khi upload xong. Đã bổ sung tham số này.

---

## 2. Đồng bộ danh sách waypoint từ GCS lên bảng trong GUI

**Lý do:**
Người dùng phản ánh: nạp mission từ ArduPilot GUI (Mission Planner/
QGroundControl) thành công, nhưng bảng "MISSION WAYPOINTS" trong app
simulator không hiển thị các waypoint đó. Nguyên nhân: bảng trên GUI chỉ
được cập nhật khi người dùng tự bấm "ADD WAYPOINT" trong app — không có
cơ chế nào đồng bộ ngược lại khi mission được nạp từ nguồn bên ngoài
(MAVLink).

**Giải pháp:**
- `gui/simulation_worker.py`:
  - Thêm signal `mission_updated = Signal(dict)`.
  - Thêm hàm `_sync_mission_table()`, gọi mỗi vòng lặp mô phỏng ngay sau
    khi xử lý message MAVLink. Hàm này lấy toàn bộ waypoint hiện tại của
    drone, so sánh với snapshot lần trước; nếu có thay đổi thì phát
    signal `mission_updated` kèm dữ liệu mới.
  - Sử dụng biến `self._last_mission_snapshot` để tránh phát signal liên
    tục khi không có gì thay đổi (đỡ tốn tài nguyên GUI).
- `gui/main_window.py`: kết nối `self.worker.mission_updated` tới
  `self.mission_panel.set_waypoints`.
- `gui/mission_panel.py`: thêm hàm `set_waypoints(payload)` để build lại
  toàn bộ bảng từ dữ liệu mission thật của drone (không phân biệt mission
  đến từ GUI hay từ GCS).

**Vì sao dùng cách "so sánh mỗi vòng lặp" thay vì hook trực tiếp vào lúc
nhận mission:**
`MissionReceiver` là một class thuần Python (không phải QObject), không
thể tự phát Qt signal. Thay vì phải truyền tham chiếu Qt signal xuyên qua
nhiều lớp (MissionReceiver → SimulationWorker), cách so sánh snapshot mỗi
tick đơn giản hơn, đồng thời tự động bắt được **mọi** nguồn thay đổi
mission (GUI, GCS, hay lệnh runtime khác) mà không cần sửa thêm chỗ nào
khác trong tương lai.

---

## 3. Cho phép chỉnh tốc độ chung của cả mission

**Lý do:**
Ban đầu, tốc độ chỉ chỉnh được theo từng waypoint riêng lẻ khi thêm thủ
công. Người dùng muốn có cách chỉnh nhanh tốc độ cho toàn bộ chu trình
mission (tất cả waypoint) mà không phải sửa từng dòng.

**Giải pháp:**
- `gui/mission_panel.py`: thêm ô nhập **"Tốc độ chung mission (m/s)"** và
  nút **"ÁP DỤNG TỐC ĐỘ"**. Khi bấm, giá trị tốc độ được ghi đè lên cột
  Speed của mọi dòng trong bảng (trừ dòng RTL, vì RTL không có khái niệm
  tốc độ hiển thị riêng) và gửi lệnh `set_mission_speed` xuống worker.
- `gui/simulation_worker.py`: thêm xử lý lệnh runtime `set_mission_speed`
  — duyệt qua toàn bộ waypoint trong `drone.mission`, gán `speed` mới;
  nếu mission đang chạy (`mission_navigator.is_active()`), áp dụng tốc độ
  đó ngay lập tức lên `flight_model.set_target_speed()` để drone đổi tốc
  độ tức thời, không cần dừng/upload lại mission.

**Vì sao áp dụng ngay cả khi đang bay:**
Nếu chỉ cập nhật giá trị `speed` trong danh sách waypoint mà không tác
động trực tiếp lên `flight_model`, người dùng sẽ phải đợi tới khi
`MissionNavigator` chuyển sang waypoint tiếp theo thì tốc độ mới mới có
hiệu lực — trải nghiệm không "tức thời". Do đó thêm bước gọi thẳng
`set_target_speed()` cho waypoint đang bay.

---

## 4. Fix lỗi: STOP mission giữa chừng rồi START lại bị bay lại từ đầu

**Lý do (bug người dùng báo):**
> "khi hoàn thành xong tôi stop tại chỗ đó và start lại thì bị bắt đầu
> lại từ đầu ko tiếp tục đi đến chỗ đó nữa"

Khi bấm STOP MISSION giữa chừng (ví dụ đang ở waypoint 2/5) rồi bấm START
MISSION lại, drone bay lại từ waypoint 1 thay vì tiếp tục từ waypoint 2.

**Nguyên nhân:**
Hàm `MissionNavigator.start()` (trong `simulator/mission_navigator.py`)
luôn luôn gọi `self.mission.start()` — hàm này ép `current_index` về `0`
(waypoint đầu tiên) mỗi khi được gọi, bất kể mission đã bay dở tới đâu.
`stop()` chỉ tắt cờ `active`, không reset `current_index`, nhưng
`start()` vẫn cứ reset lại từ đầu mỗi lần được gọi.

**Giải pháp:**
Sửa `MissionNavigator.start()`: trước khi reset về waypoint 1, kiểm tra
xem mission có đang "dở dang" hay không (`mission.is_started()` = True,
`mission.is_finished()` = False, và vẫn còn waypoint hiện tại hợp lệ).
Nếu đúng, chỉ bật lại `active = True` và tiếp tục từ waypoint hiện tại
(gọi `_set_current_waypoint_target()` để đặt lại target điều hướng),
**không** gọi `mission.start()`. Chỉ khi mission đã hoàn thành
(`is_finished() == True`) hoặc chưa từng bắt đầu, mới reset về waypoint 1
như hành vi cũ.

**Vì sao không ảnh hưởng các trường hợp khác (disarm, đổi mode bay...):**
Đã kiểm tra toàn bộ các nơi gọi `mission_navigator.stop()` trong
`simulator/drone.py` (disarm, chuyển sang ALT_HOLD, chuyển sang FREE
flight...). `disarm()` chỉ được phép khi drone không ở trên không
(`not self.state.airborne`), nên không xảy ra tình huống resume giữa
không trung sau khi disarm. Các trường hợp chuyển mode khác gọi
`mission_navigator.start()` chỉ khi mission chưa active
(`if not self.mission_navigator.is_active()`), nên hành vi cũ vốn đã là
"tiếp tục" — không bị thay đổi bởi fix này.

**Đã kiểm chứng bằng script test (`test_resume.py`):** tạo mission 3
waypoint, bay tới WP2, gọi `stop()`, gọi `start()` lại → xác nhận resume
đúng tại WP2 thay vì quay về WP1.

---

## 5. Bảng waypoint dễ nhìn hơn + hiển thị trạng thái từng điểm

**Lý do:**
> "list danh sách bị quá nhỏ và gắn thêm khi thực hiện xong điểm đó có ô
> hiện dấu tích"

Bảng waypoint bị giới hạn chiều cao cố định 180px, khó xem khi mission có
nhiều điểm. Ngoài ra không có cách nào biết trực quan waypoint nào đã bay
xong, đang bay tới, hay còn chờ.

**Giải pháp:**
- `gui/mission_panel.py`:
  - Tăng chiều cao bảng: `setMinimumHeight(260)` +
    `setMaximumHeight(400)` (trước đó chỉ có `setMaximumHeight(180)`).
  - Thêm cột mới **"Trạng thái"** vào cuối bảng.
  - Cập nhật `set_waypoints()` để tính trạng thái từng dòng dựa trên dữ
    liệu tiến trình mission (`current_index`, `active`, `finished`) nhận
    được từ signal `mission_updated`:
    - `✓` — nếu mission đã hoàn thành, hoặc waypoint đó có số thứ tự nhỏ
      hơn waypoint hiện tại (đã bay qua).
    - `➤` — nếu đây là waypoint đang được bay tới (`index == current_index`
      và mission đang active).
    - Trống — nếu chưa tới lượt.
  - `_add_row()` / `_add_rtl_row()` (thêm thủ công qua GUI): thêm ô
    trạng thái rỗng cho dòng mới, để khớp số cột với `set_waypoints()`.
- `gui/simulation_worker.py`: mở rộng dữ liệu snapshot phát ra trong
  `_sync_mission_table()` để bao gồm thêm `current_index`
  (`drone.mission.get_current_index()`), `active`
  (`drone.mission_navigator.is_active()`), và `finished`
  (`drone.mission.is_finished()`) — trước đó signal chỉ mang danh sách
  waypoint thuần, không có thông tin tiến trình.

**Vì sao đổi kiểu dữ liệu của signal `mission_updated` từ `list` sang
`dict`:**
Ban đầu signal chỉ gửi list waypoint (phục vụ mục 2). Để thêm được cột
trạng thái, cần gửi kèm thông tin tiến trình mission (đang ở đâu, đã
xong chưa), nên đổi payload thành dict gồm cả `waypoints`,
`current_index`, `active`, `finished` — gói gọn trong một signal duy
nhất, tránh phải thêm signal thứ hai chỉ để đồng bộ trạng thái.

---

## Các file đã chỉnh sửa

| File | Thay đổi chính |
|---|---|
| `simulator/mission.py` | Thêm trường `action` vào `Waypoint` |
| `simulator/mission_navigator.py` | Fix resume mission sau STOP/START |
| `mavlink/mission_receiver.py` | Hỗ trợ RTL trong mission upload/download, fix mất `action` khi finish upload |
| `gui/simulation_worker.py` | Signal `mission_updated`, đồng bộ bảng mission, lệnh `set_mission_speed` |
| `gui/mission_panel.py` | Nút ADD RTL, ô tốc độ chung mission, cột Trạng thái, bảng cao hơn, `set_waypoints()` |
| `gui/main_window.py` | Kết nối signal `mission_updated` → `mission_panel.set_waypoints` |

## Kiểm thử đã thực hiện

- Test logic độc lập (`test_rtl_mission.py`): WP1 → RTL (về home) → WP3,
  xác nhận thứ tự và tọa độ RTL đúng.
- Test logic độc lập (`test_resume.py`): STOP giữa chừng ở WP2 → START
  lại → xác nhận tiếp tục đúng tại WP2.
- Chạy lại toàn bộ ứng dụng (`main.py`) sau mỗi lần sửa để xác nhận không
  có lỗi cú pháp / lỗi khởi động.
- **Chưa test:** thao tác thực tế trên GUI (kéo thả, bấm nút bằng chuột)
  và luồng mission upload thật từ Mission Planner/QGroundControl qua kết
  nối MAVLink — cần người dùng xác nhận trên máy thật.
