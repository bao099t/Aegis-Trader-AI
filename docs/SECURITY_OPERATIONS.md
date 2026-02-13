# 🛡️ HƯỚNG DẪN VẬN HÀNH AN NINH (SECURITY OPERATIONS)

**Ngày cập nhật**: 2026-02-13 (Phase 61)
**Cấp độ bảo mật**: ZERO TRUST

---

## 1. Cơ Chế Hard Stop-Loss (Cắt Lỗ Cứng)
Hệ thống KHÔNG còn lưu điểm cắt lỗ trong bộ nhớ RAM.
*   **Cơ chế**: Ngay khi lệnh Mua (BUY) khớp, Bot sẽ gửi ngay 1 lệnh Bán (SELL STOP-MARKET) lên sàn với giá Trigger = Giá Mua - 5% (hoặc theo AI).
*   **Ưu điểm**:
    *   Mất mạng: Sàn vẫn tự bán giúp bạn.
    *   Sập nguồn: Sàn vẫn tự bán giúp bạn.
    *   Sàn bị hack API: Lệnh đã nằm trên sổ lệnh (Order Book) của sàn, hacker không hủy được nếu không có quyền.

## 2. Khôi Phục Dữ Liệu (Disaster Recovery)
Nếu máy tính bị hỏng ổ cứng hoặc dữ liệu bị lỗi:
1.  Vào thư mục `data/backups/`.
2.  Tìm file mới nhất (ví dụ: `alerts_20260213.db`).
3.  Copy ra thư mục `data/` và đổi tên thành `alerts.db`.
4.  Chạy lại `start_all.bat`.

## 3. API Security
API Server chạy tại `http://127.0.0.1:8000`.
*   **Mặc định**: Chỉ máy tính này (Localhost) mới truy cập được.
*   **Key**: Nếu bạn cần gọi API từ App khác, hãy dùng Header:
    `X-AEGIS-KEY: aegis_local_dev`
*   **Đổi Key**: Sửa file `.env`:
    `AEGIS_API_KEY=MatKhauSieuKho123`

## 4. Chế Độ "Blind Mode" (Mù)
Nếu mất kết nối Internet:
1.  Bot sẽ phát hiện qua `monitor.py`.
2.  Tự động chuyển sang chế độ "Phòng thủ":
    *   Hủy toàn bộ lệnh chờ mua (Pending Buy).
    *   Giữ nguyên lệnh Stop-Loss (vì đã nằm trên sàn).
    *   Không đặt lệnh mới.
    *   Không đặt lệnh mới.
    *   Ghi Log: "Offline - Defense Mode Activated".

## 5. Chống Spam & DDoS (Rate Limiting)
*   **API Protection**: Giới hạn 60 requests/phút cho mỗi IP. Ngăn chặn việc spam lệnh làm treo hệ thống.
*   **Middleware**: Tích hợp sẵn trong `src/api/server.py`.

## 6. Nút Khẩn Cấp (Panic Button)
Trong trường hợp thị trường sập bất ngờ hoặc có tin chiến tranh:
1.  Truy cập Dashboard (`http://localhost:3000`).
2.  Nhấn nút đỏ **"EMERGENCY LIQUIDATION"**.
3.  Hệ thống sẽ ngay lập tức bán toàn bộ tài sản theo giá thị trường (Market Order) để bảo toàn vốn.

---
*Tài liệu này dùng cho SysAdmin và Vận hành viên.*
