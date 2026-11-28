# Reflection — Vũ Quang Huy

> Làm ở guide bước 5.3. Mỗi người một file: chép file này thành `reflection/<ten-khong-dau>.md` (viết thường, không dấu). Hạn: **23:59 Thứ Bảy 28/11**. Mỗi câu 3–6 dòng.

1. Vai trò + phần mình làm (trỏ tới file / commit):
   AI Agent cùng Cao. Theo lịch sử commit: nhập đề từ PDF và nối với chat học sinh (#3, PR #29, commit beede0c), cấu hình production backend và runbook EC2 (#13, PR #42, commit fdf7a91, 1f7900c), cá nhân hóa đề ôn từ lượt đã chấm: thống kê chương gần đây, kiểm đề xuất AI, mở đề ôn từ kết quả đã chấm (#41, PR #46, commit 612b2c0, 014ad31, b35f684, 9ac6acd). *(Huy bổ sung hoặc sửa cho đúng phần mình làm.)*

2. AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):
   Theo `docs/ai-usage.md`: Codex rà cấu hình backend, thêm ánh xạ khóa AI trong Compose, cập nhật runbook EC2 (#13) và đọc luồng #40, triển khai thống kê từ lượt đã chấm, nối đề xuất AI với bản xem trước, viết ca kiểm thử (#41). Phần mình duyệt: phạm vi và ngưỡng thống kê, đối chiếu số liệu và bản xem trước khi duyệt PR, xác minh trên EC2. *(Huy bổ sung chỗ cụ thể nào của output phải sửa lại.)*

3. Một câu thử trượt của nhóm và mình học được gì từ nó:
   *(Huy tự chọn một câu trong `eval/run-1.csv` hoặc `eval/run-2.csv` và viết bài học của mình; ví dụ B15 hoặc B17 còn trượt ở lượt 2.)*
