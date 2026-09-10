# Quy trình Nạp và Thực thi Nhiệm vụ Bay (Mission Write & Flight)

Tài liệu này mô tả chi tiết luồng bắt tay (Handshake) giao thức MAVLink để nạp danh sách Waypoint từ ứng dụng GCS vào bộ mô phỏng, cơ chế thực thi bay tự động và các khuyến nghị khi lập trình nhiệm vụ.

---

## 1. Luồng truyền nhận MAVLink (MAVLink Flow)

Trình mô phỏng triển khai đầy đủ quy trình bắt tay chuẩn MAVLink Mission Protocol:

1. **GCS / Ứng dụng điều khiển** gửi bản tin `MISSION_COUNT` (chứa tổng số lượng $N$ mục nhiệm vụ).
2. **Simulator** phản hồi `MISSION_REQUEST_INT(seq=0)` để yêu cầu điểm đầu tiên.
3. **GCS / Ứng dụng điều khiển** gửi bản tin `MISSION_ITEM_INT(seq=0)`.
4. **Simulator** lưu mục vào vùng đệm tạm thời (`staging_mission`) và tiếp tục yêu cầu điểm tiếp theo `MISSION_REQUEST_INT(seq=1)`.
5. Quy trình lặp lại tuần tự cho đến khi Simulator nhận đủ $N$ mục.
6. **Simulator** gửi bản tin xác nhận `MISSION_ACK(MAV_MISSION_ACCEPTED)`.
7. Danh sách nhiệm vụ mới sẽ thay thế toàn bộ nhiệm vụ đang hoạt động một cách nguyên tử (Atomic Commit).

### Các lệnh điều hướng được hỗ trợ:
- `MAV_CMD_NAV_TAKEOFF`: Cất cánh đạt độ cao chỉ định.
- `MAV_CMD_NAV_WAYPOINT`: Bay đến điểm tọa độ và dừng chờ theo thời gian (`hold_time`).
- `MAV_CMD_NAV_LOITER_TIME`: Bay đến điểm và lượn treo cố định vị trí theo thời gian thiết lập.
- `MAV_CMD_NAV_LAND`: Hạ cánh thẳng đứng tại tọa độ chỉ định.
- `MAV_CMD_NAV_RETURN_TO_LAUNCH (RTL)`: Bay về tọa độ Home ban đầu.
- `MAV_CMD_DO_CHANGE_SPEED`: Thay đổi tốc độ bay (`param2`) áp dụng cho các điểm Waypoint tiếp theo.

---

## 2. Quá trình Thực thi Nhiệm vụ (Mission Execution)

Sau khi quá trình nạp nhiệm vụ hoàn tất:

1. **Khởi chạy nhiệm vụ**:
   - Chọn chế độ bay `AUTO` (từ GCS) hoặc `MISSION` (trên giao diện Simulator).
   - Mở khóa động cơ (**ARM**).
   - Nếu nhiệm vụ đã được nạp sẵn, Drone sẽ tự động bắt đầu bay theo lộ trình.
   - Nếu Drone đã được ARM và đang ở chế độ `AUTO` / `MISSION` khi quá trình nạp kết thúc, nhiệm vụ mới sẽ tự động bắt đầu ngay lập tức.
2. **Bám lộ trình bay**:
   - Simulator tự động điều khiển bám theo: Vĩ độ (Latitude), Kinh độ (Longitude), Độ cao (Altitude), Tốc độ từng chặng, Bán kính chấp nhận điểm đến (Acceptance Radius) và Thời gian dừng chờ (Hold Time).
   - **Xử lý đặc biệt cho lệnh `LAND`**: Không kết thúc nhiệm vụ ở sai số độ cao thông thường (1m), Drone sẽ tiếp tục hạ cánh từ từ chạm đất ($0.0\,\text{m}$) rồi mới hoàn tất và tự động ngắt Arm (`DISARMED`).
3. **Phát tín hiệu giám sát**:
   - Simulator liên tục phát bản tin `MISSION_CURRENT` (chỉ số Waypoint đang bay tới) và `MISSION_ITEM_REACHED` (khi đã hoàn thành một Waypoint).

---

## 3. Khuyến nghị cấu hình cho Ứng dụng GCS

Đối với một nhiệm vụ bay quét bản đồ hoặc tuần tra tiêu chuẩn, cấu trúc lộ trình khuyến nghị như sau:

$$\text{TAKEOFF} \longrightarrow \text{WAYPOINT}_1 \longrightarrow \text{WAYPOINT}_2 \longrightarrow \dots \longrightarrow \text{RTL / LAND}$$

- Sử dụng hệ quy chiếu `MAV_FRAME_GLOBAL_RELATIVE_ALT_INT` cho độ cao nếu ứng dụng thiết lập độ cao tương đối so với điểm xuất phát (Home).
- **Cấu trúc một Waypoint tiêu chuẩn**:
  - `frame`: `MAV_FRAME_GLOBAL_RELATIVE_ALT_INT` (Độ cao tương đối).
  - `command`: `MAV_CMD_NAV_WAYPOINT` (Mã số 16).
  - `param1`: Thời gian dừng chờ tại điểm (giây).
  - `param2`: Bán kính chấp nhận điểm đích (mét).
  - `param4`: Góc xoay mũi mong muốn (độ, $0 - 360^\circ$).
  - `x`: $\text{Vĩ độ} \times 10^7$ (int32).
  - `y`: $\text{Kinh độ} \times 10^7$ (int32).
  - `z`: Độ cao tương đối (mét, float).

---

## 4. Lưu ý quan trọng

Trình mô phỏng là môi trường kiểm thử logic bay, giải thuật điều hướng và tương tác MAVLink với trạm mặt đất. Đây là mô hình vật lý giả lập phục vụ phát triển phần mềm, không thay thế hoàn toàn cho các thử nghiệm khí động học thực tế chuyên sâu trên phần cứng máy bay thật.
