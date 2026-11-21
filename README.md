# KPI Dashboard Web - Team CTO 1 (Google Sheets Live Data)

Bộ công cụ hiển thị Website Dashboard KPI & Tiến độ ca trực cho Team CTO 1, thuần **HTML / CSS / JavaScript**, kết nối và đọc trực tiếp dữ liệu từ Google Sheets qua trình duyệt (không cần cài đặt Python hay môi trường phức tạp).

---

## 📁 Danh sách tệp & Cấu trúc

| Tệp / Thư mục | Chức năng |
|---|---|
| `index.html` / `kpi_dashboard.html` | File giao diện Web chính của Dashboard (chạy trực tiếp trên mọi trình duyệt, tích hợp đầy đủ 3 phân hệ: KPI, Lịch trực & Tra cứu Copy OT) |
| `schedule.html` | Trang riêng biệt hiển thị chuyên sâu **Lịch Trực Ca & Chấm Công** (vào thẳng tab Lịch trực) |
| `ot_tracker.html` | Trang riêng biệt hiển thị chuyên sâu **Tra Cứu & 1-Click Copy Giờ Overtime (OT)** |
| `css/` | Thư mục chứa các module giao diện CSS độc lập:<br>• `main.css`: Theme tối/sáng, Typography, Header, Navigation, Chế độ TV Kiosk, Responsive<br>• `kpi.css`: Pacing banner, Top cards, Bảng KPI & Hiệu suất, Modal, Podium<br>• `schedule.css`: Ma trận lịch trực, bộ lọc chu kỳ ngày, bảng chấm công<br>• `ot_tracker.css`: Search autocomplete, quick chips, 3 bảng horizontal copy, bảng chi tiết |
| `js/` | Thư mục chứa các module JavaScript độc lập:<br>• `data.js`: Dữ liệu khởi tạo mặc định (offline fallback) & khôi phục cache<br>• `sheets_api.js`: Kết nối trực tiếp Google Sheets qua WebCrypto RSA-SHA256, tự động đồng bộ Realtime<br>• `kpi.js`: Tính toán KPI, Pacing, bộ lọc ca/nhân viên, tháp vinh danh, xuất CSV/Excel<br>• `schedule.js`: Parse dữ liệu lịch trực thô, render ma trận chấm công, phân tích OFF/Phép<br>• `ot_tracker.js`: Tự động tính giờ OT (Sáng, Trưa, Tối), loại trừ phép, copy 1-click chuẩn TSV dán Sheets<br>• `app.js`: Điều hướng SPA, switch tabs, chế độ TV, Dark/Light theme, đồng bộ URL Hash |
| `Run_Website.bat` | Phím tắt nhấp đúp để mở ngay Dashboard trên trình duyệt mặc định |
| `kpi_data.json` | File lưu dữ liệu dự phòng (Offline fallback) |
| `Data/` | Thư mục lưu cache lịch trực (`schedule_cache.json`) dự phòng |
| `_backup_python_tools.zip` | Tệp nén lưu trữ toàn bộ các script Python cũ (đã sao lưu an toàn) |

---

## 🚀 Các tính năng chính của Website

1. **📊 Báo Cáo & Tiến Độ KPI:**
   - Theo dõi % hoàn thành KPI Ticket, Công việc (CV) và Pacing theo ngày hiện tại trong tháng.
   - Tháp vinh danh Podium Top 3, thẻ năng lực cá nhân và máy tính dự báo cán đích cuối tháng.

2. **📅 Lịch Trực & Chấm Công (Team CTO 1):**
   - Ma trận lịch trực 13 nhân sự theo ngày, lọc theo chu kỳ 26-25 hoặc đầu-cuối tháng.
   - Bảng đối soát ngày OFF, ngày Phép, ngày Làm việc.

3. **⏰ Tra Cứu, Đối Chiếu & 1-Click Copy Giờ OT (Unified Overtime Matrix):**
   - **Tự động tính toán giờ OT:** Theo chu kỳ 26 tháng trước đến 25 tháng này (Ca Sáng 1h, Ca Trưa 1h, Ca Tối 3h hoặc 4h với N, FB). Tự động loại trừ ngày nghỉ phép cả ngày (P) hoặc ca chiều (CH).
   - **Ma Trận Đối Chiếu Hàng Ngang Duy Nhất:** Hàng trên hiển thị các ca thực tế trên Lịch trực (`S`, `TR`, `T`, `OFF`, `P`, `HC`), các hàng dưới là số giờ OT tương ứng của từng ca (`Ca Tối`, `Ca Trưa`, `Ca Sáng`) và dòng `Tổng Giờ OT`.
   - **Chỉnh sửa trực tiếp (Inline Editing):** Nhấp chuột trực tiếp vào bất kỳ ô ngày nào của các hàng ca để sửa/thêm số giờ phát sinh. Dòng Tổng giờ OT và các thẻ tóm tắt sẽ tự động cộng dồn theo thời gian thực!
   - **1-Click Copy Chuẩn TSV (Google Sheets / Excel):**
     - Nút `📋 Copy Cả 3 Ca`: Sao chép 3 dòng đồng thời (Ca Tối, Ca Trưa, Ca Sáng) để dán 1 phát ăn ngay 3 dòng vào Google Sheets.
     - Nút `🗐 Copy` trên từng hàng: Sao chép riêng hàng Ca Tối, Ca Trưa, Ca Sáng hoặc Tổng giờ.
   - Nút `↺ Đặt lại` để khôi phục nhanh công thức tính tự động ban đầu.
   - Bảng tổng hợp giờ OT toàn team CTO 1 cho phép chuyển nhanh giữa các bạn.

---

## 🚀 Hướng dẫn sử dụng nhanh

1. **Mở Website:**
   - Nhấp đúp chuột vào file `Run_Website.bat` (hoặc mở trực tiếp file `index.html` / `kpi_dashboard.html`).
   - Web sẽ tự động mở trên Chrome, Edge hoặc trình duyệt mặc định của máy.

2. **Cơ chế cập nhật dữ liệu tự động (Realtime):**
   - Khi mở trang web, JavaScript sẽ tự động kết nối và đọc số liệu mới nhất trực tiếp từ Google Sheets.
   - Web có cơ chế tự động làm mới mỗi 30 giây một lần.
   - Anh cũng có thể bấm nút **"🔄 Tải lại số liệu mới nhất"** hoặc **"🔄 Tải lại Lịch Trực Mới Nhất"** để ép làm mới tức thì.

---

## 🔗 Nguồn dữ liệu Google Sheets

- **Sheet KPI & Hiệu suất ca:** `https://docs.google.com/spreadsheets/d/1Gp4UVa_6YyQHA9SZxts8ey9z_mwB3j-BEKx20fvPPfk/edit`
  - Tab `KPI tong`: Bảng tổng hợp KPI các bạn nhân viên.
  - Tab `HS ca truc`: Bảng chi tiết hiệu suất theo từng ca trực.
- **Sheet Lịch trực:** `https://docs.google.com/spreadsheets/d/1ct8owykbsFzzlvjBHAPk_I44tr9bSbGB5KI4d5jJixo/edit`
