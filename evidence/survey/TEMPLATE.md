# Khảo sát — mẫu form và cách lưu kết quả

> Điền ở guide bước 1.2. Không khảo sát thì xoá thư mục này.
> Ngưỡng: **≥20 người ngoài nhóm, đúng người dùng**, giữ log đủ câu hỏi và từng câu trả lời.

> **Cập nhật 27/11/2026:** form đã phát với bộ câu hỏi khác bản nháp dưới đây. Bộ câu hỏi thực tế và cách đếm: [`questions.md`](questions.md). Kết quả ẩn danh: [`results.csv`](results.csv).

## Mẫu form *(bản nháp ban đầu, đã thay bằng `questions.md`)*

Kênh dự kiến: Google Form gửi tới học sinh lớp 10–12 tại trung tâm dạy thêm nơi Nguyễn Minh Đức đang làm quản lý. Nhóm đặt mục tiêu có ≥20 phản hồi hợp lệ từ học sinh ngoài nhóm đã từng tự ôn bằng đề Toán.

8–10 câu, hỏi **hành vi đã xảy ra**, không hỏi "có thích không".

| # | Câu hỏi | Kiểu trả lời |
|---|---|---|
| 1 | Bạn đang học lớp nào? | Lớp 10 · lớp 11 · lớp 12 · khác |
| 2 | Lần gần nhất bạn tự ôn bằng một đề Toán là khi nào? | Hôm nay · trong 7 ngày qua · 8–30 ngày trước · lâu hơn · chưa từng |
| 3 | Lần đó bạn ôn cho việc gì? | Bài kiểm tra · thi học kỳ · thi tốt nghiệp THPT · ôn định kỳ · khác |
| 4 | Sau khi chữa đề, bạn đã làm gì để quyết định ôn tiếp phần nào? | Chọn nhiều: xem lỗi và lời giải · hỏi người khác · tự chọn đề khác · chưa chọn · khác |
| 5 | Lần đó bạn có chọn được phần hoặc bài tập để ôn tiếp không? | Có · chọn được một phần · không · không cần ôn tiếp |
| 6 | Lần đó bạn mất khoảng bao lâu để quyết định ôn gì và tìm bài để làm tiếp? | Dưới 5 phút · 5–14 phút · 15–30 phút · trên 30 phút · không nhớ / không tìm |
| 7 | Trong 30 ngày qua, có bao nhiêu lần chữa đề xong mà bạn chưa biết ôn phần nào tiếp? | Số · không nhớ |
| 8 | Lần gần nhất đó, bạn đối chiếu đề ôn với nội dung hoặc cấu trúc bài thi bằng cách nào? | Xem tài liệu của trường / cơ quan tổ chức · hỏi người khác · dựa vào mô tả của đề · không đối chiếu · không áp dụng · khác |
| 9 | Có điều gì khiến việc chọn phần hoặc đề ôn tiếp dễ hay khó hơn ở lần đó? | Đoạn văn, tuỳ chọn |

Không thu tên, email, mã học viên hoặc thông tin liên hệ trong form. Nếu chọn “chưa từng” ở câu 2 hoặc “khác” ở câu 1, kết thúc trước nhóm câu về lần làm bài gần nhất.

## Lưu vào thư mục này

- `questions.md` — nguyên bộ câu hỏi + kênh đã gửi + giờ mở / chốt.
- `results.csv` — bản xuất **đã xoá** mọi cột nhận ra người trả lời. Bản gốc còn thông tin cá nhân thì **không** commit.
- Số chính + ≥3 câu trả lời nguyên văn → chép vào `evidence/summary.md`. Dưới khoảng 10 người thì chỉ ghi x/n, không ghi %.
