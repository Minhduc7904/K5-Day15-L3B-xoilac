# Mẫu cấu trúc đề (ma trận) nạp sẵn

Migration `0019_seed_exam_template_matrix` nạp 14 mẫu môn Toán vào bảng `exam_templates` (API: [mẫu cấu trúc đề](../api/exam-templates-api.md)). Mã chương khớp `data/chapters.csv`; không có khoá ngoại nên nạp được trước gói seed nền.

| Mẫu | Trạng thái | Độ tin cậy |
| --- | --- | --- |
| Tốt nghiệp THPT 2025, 2026 (22 câu = 12 nhiều lựa chọn + 4 đúng/sai + 6 trả lời ngắn, 90 phút) | `APPROVED` | Cấu trúc tổng có nhiều nguồn báo chí. **Không có số câu theo chương**: chỉ có phạm vi chương, vì ma trận chính thức của Bộ ở dạng ảnh hoặc không truy cập được |
| Toán 12 GK1, CK1, GK2, CK2 (2025-2026) | `DRAFT` | Cấu trúc theo đề tốt nghiệp (nguồn tuyensinhso.vn, chỉ GK1). Phạm vi chương theo phân phối chương, phần còn lại *(tự ước tính)* |
| Toán 11 GK1 (2025-2026) | `DRAFT` | Đọc đủ từ ma trận THPT Ngô Gia Tự (Đắk Lắk): 12/3/4 + 3 tự luận, có mức nhận biết/thông hiểu và số câu theo chương trong `description`. Là ma trận của một trường |
| Toán 10 và 11 các kỳ còn lại | `DRAFT` | *(tự ước tính)* theo cấu trúc Ngô Gia Tự; phạm vi chương theo sách Kết nối tri thức |

Bộ GD&ĐT không ban hành ma trận giữa kỳ, cuối kỳ chung; mỗi trường tự ra. Admin cần đối chiếu với ma trận của trường rồi sửa (`PUT`) và duyệt (`POST .../approve`) từng mẫu `DRAFT` trước khi pipeline học sinh dùng được.

Kiểm tra: `cd backend && pytest tests/test_seed_exam_template_matrix.py`; migration đã chạy `upgrade head`, `downgrade`, `upgrade head` trên PostgreSQL 16, mỗi lần 14 dòng, không trùng.
