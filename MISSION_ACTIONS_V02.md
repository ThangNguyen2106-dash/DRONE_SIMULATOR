# Danh mục Lệnh Hành động Nhiệm vụ (Mission Actions V02)

Quá trình nạp nhiệm vụ được hiểu như một chuỗi các mục MAVLink Mission Items. Các lệnh điều hướng (Navigation Items) điều khiển máy bay di chuyển trong không gian; các lệnh hành động / điều kiện (DO Commands) được gắn kèm vào điểm điều hướng phía trước và được kích hoạt thực thi sau khi máy bay chạm đến điểm Waypoint đó.

---

## 1. Danh sách các Lệnh Hành động được Hỗ trợ

- **`MAV_CMD_NAV_WAYPOINT`**: Bay đến tọa độ chỉ định, bao gồm thời gian dừng chờ tại điểm (`param1`, tính bằng giây).
- **`MAV_CMD_NAV_LOITER_TIME`**: Bay đến vị trí và lượn treo cố định vị trí trong khoảng thời gian `param1` (giây).
- **`MAV_CMD_NAV_TAKEOFF`**: Lệnh cất cánh tự động đạt độ cao mục tiêu.
- **`MAV_CMD_NAV_LAND`**: Lệnh hạ cánh thẳng đứng tại tọa độ chỉ định.
- **`MAV_CMD_NAV_RETURN_TO_LAUNCH (RTL)`**: Lệnh quay về điểm xuất phát (Home); sau khi chạm điểm phía trước, chế độ RTL kích hoạt và hệ thống tự động điều hướng máy bay về Home rồi hạ cánh.
- **`MAV_CMD_NAV_DELAY`**: Chuyển đổi thành tác vụ giữ vị trí (HOLD) theo thời gian định sẵn.
- **`MAV_CMD_DO_CHANGE_SPEED`**: Thay đổi tốc độ bay áp dụng cho toàn bộ các điểm điều hướng tiếp theo.
- **`MAV_CMD_IMAGE_START_CAPTURE`**: Kích hoạt chụp ảnh tại điểm Waypoint.
- **`MAV_CMD_IMAGE_STOP_CAPTURE`**: Dừng quay video / ghi hình camera.
- **`MAV_CMD_DO_SET_CAM_TRIGG_DIST`**: Bật cơ chế kích hoạt chụp ảnh tự động theo khoảng cách di chuyển.
- **`MAV_CMD_DO_GIMBAL_MANAGER_PITCHYAW`**: Thiết lập góc ngẩng/quay (Pitch/Yaw) cho cụm camera Gimbal giả lập.
- **`MAV_CMD_DO_SET_SERVO`**: Giả lập đóng/mở ngàm thả hàng hoặc kích hoạt kênh Servo.
- **`MAV_CMD_DO_SET_RELAY`**: Giả lập đóng/ngắt rơ-le điện (Relay State).
- **`MAV_CMD_DO_SET_ROI`**: Thiết lập tọa độ điểm quan sát trọng tâm (Region of Interest - ROI) để camera luôn tự động hướng về điểm này.

---

## 2. Ví dụ: Bay chu trình Waypoint rồi tự động bay về nhà (RTL)

Ứng dụng Mission Planner hoặc QGroundControl có thể gửi chuỗi lệnh:

```text
WP1 (Tọa độ 1)
WP2 (Tọa độ 2)
MAV_CMD_NAV_RETURN_TO_LAUNCH
```

Simulator sẽ tự động liên kết lệnh RTL vào điểm `WP2` trong quá trình nạp. Trình tự thực thi:

$$\text{WP1} \longrightarrow \text{WP2} \longrightarrow \text{Đạt WP2} \longrightarrow \text{Kích hoạt RTL} \longrightarrow \text{Bay về HOME} \longrightarrow \text{Hạ cánh} \longrightarrow \text{HOLD / Tắt Arm}$$

Lệnh RTL là hành động kết thúc chu trình nhiệm vụ.

---

## 3. Ví dụ: Nhiệm vụ Khảo sát Quét bản đồ (Mapping Mission)

```text
1. TAKEOFF 30m                  (Cất cánh lên độ cao 30m)
2. WP1 + Dừng 10s + Chụp ảnh    (Bay đến WP1, dừng 10s và chụp ảnh)
3. WP2 + Chúc Gimbal + Chụp ảnh (Bay đến WP2, xoay Gimbal chúc xuống và chụp ảnh)
4. WP3 + Chụp mỗi 5m            (Bay đến WP3, tự động chụp ảnh mỗi khoảng cách 5m)
5. WP4                          (Bay đến WP4)
6. RTL                          (Tự động quay về Home và hạ cánh an toàn)
```

Dữ liệu hình ảnh và nhật ký tọa độ giả lập được ghi vào thư mục `simulation_data/photos/`.
