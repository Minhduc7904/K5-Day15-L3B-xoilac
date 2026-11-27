# Pipeline nhập đề PDF

Issue #3 đưa câu hỏi từ đề Toán THPT vào kho chung sau khi admin kiểm tra. Tài liệu này mô tả hợp đồng triển khai và các mốc kiểm chứng.

## Bối cảnh và ràng buộc

Backend dùng PostgreSQL, MinIO và schema nền từ migration `0002`. PDF cần có quyền sử dụng. Mistral trích xuất các trang và hình. OpenAI tách câu, đáp án và lời giải từ nội dung nguồn. Admin xét từng câu trước khi xuất bản.

## Thành phần và trách nhiệm

| Lớp | Trách nhiệm |
| --- | --- |
| API | Nhận PDF có giới hạn dung lượng, kiểm quyền admin, trả mã phiên và URL theo dõi. |
| Use case | Điều phối các bước, đối chiếu đáp án, kiểm điều kiện duyệt và xuất bản trong một giao dịch. |
| Service | Gọi OCR, Structured Outputs và embedding. Lưu đối tượng qua storage service hiện có. |
| Repository | Lưu phiên, câu nháp và embedding. Dùng chung bảng `media`, `questions`, `statements`, `questions_chapters`. |

## Luồng dữ liệu và tích hợp

1. Lưu PDF gốc và tạo phiên `queued`. Tác vụ nền dùng session DB riêng, đặt trạng thái `processing` rồi cập nhật bước đang chạy.
2. Lưu Markdown từng trang để đối chiếu. Lưu ảnh với quan hệ đến PDF gốc và gắn mã `media:ID` ổn định vào Markdown. Ảnh thiếu hoặc lỗi lưu được báo để admin kiểm tra.
3. Tách câu và đáp án theo phần và số in trên đề. Giữ thứ tự, LaTeX, trang nguồn, ảnh và lời giải có trong PDF. Gắn cờ đáp án thiếu, mâu thuẫn hoặc ghép không duy nhất. Giá trị chưa rõ của mệnh đề là `null`.
4. So sánh embedding của thân câu và các mệnh đề với một mẫu câu Toán đã xuất bản, có nhãn hợp lệ. Lưu mã câu gần và điểm tương đồng. Để trống nhãn thiếu căn cứ.
5. Trả `ready_for_review` khi có bản nháp hoặc `failed` kèm bước lỗi. Admin sửa, duyệt hoặc bỏ từng câu. Khi duyệt, ghi câu và các liên kết vào kho chung với `visibility=PUBLISHED`. Bản đọc cho học sinh chỉ gồm nội dung, mệnh đề có thứ tự và ảnh được phép đọc.

## Quyết định và cách kiểm chứng

MVP dùng FastAPI BackgroundTasks. Nếu tiến trình dừng trong lúc xử lý, lần tải lại PDF tạo một phiên mới. OCR mặc định dùng Mistral với model cấu hình được. Tệp gốc và hình nằm trong MinIO riêng tư. URL xem hình có thời hạn đi qua backend để trình duyệt dùng được khi MinIO nằm trong mạng Docker.

| Mốc | Bằng chứng hoàn thành |
| --- | --- |
| 1. Tài liệu và mẫu | Hai tài liệu được viết trước nghiệp vụ. Mẫu PDF chữ có đáp án đã được kiểm. |
| 2. Luồng đầu tiên | Một câu có hình được tải lên, tách, xem ảnh, duyệt và đọc từ kho. |
| 3. Các ca trích xuất và duyệt | Kiểm năm loại câu, số câu lặp, đáp án thiếu hoặc mâu thuẫn, hình trong thân câu, mệnh đề và lời giải. |
| 4. Gợi ý nhãn | Câu gần có mã và điểm tương đồng. Câu thiếu căn cứ được để trống nhãn. |
| 5. Nghiệm thu | Chạy PDF chữ và PDF scan. Kiểm bản đọc sau duyệt và cập nhật ví dụ API. |

- [x] Mốc 1. Đã đối chiếu đề mẫu, trang hình và đáp án. Đã viết tài liệu trước code nghiệp vụ.
- [x] Mốc 2. Đã kiểm từ tải lên đến câu xuất bản và URL ảnh qua API. Test dùng phản hồi nhà cung cấp giả lập và kho tệp trong bộ nhớ.
- [x] Mốc 3. Đã kiểm năm loại câu, số câu lặp, đáp án xung đột, mệnh đề chưa rõ, hình thiếu và câu bị từ chối. Bộ test backend có 49 ca đạt tại mốc này.
- [ ] Mốc 4. Kiểm gợi ý nhãn bằng chỉ mục câu đã duyệt.
- [ ] Mốc 5. Nghiệm thu với nhà cung cấp và hạ tầng thật.

Mẫu tại máy nhóm `data/example_exam.pdf` có 15 trang. Phần I câu 6 có bốn đồ thị trên trang 2 và đáp án D trên trang 7. Phần I câu 5 qua ranh giới trang 1–2. PDF có lớp văn bản. Ca scan cần thêm bản ảnh hoặc fixture ảnh tương đương.

Chạy từ thư mục gốc trên Windows bằng `..venv\Scripts\python.exe -m pytest -q backend`. Test sinh PDF có lớp chữ và PDF chỉ có ảnh. Các test tách câu dùng phản hồi OCR và OpenAI cố định để tái hiện các trường hợp biên.

## Tài liệu liên quan

- [API nhập đề PDF](api.md)
- [Các lớp backend](../../architecture/backend-layers.md)
- [Chạy bộ khung local](../../operations/run-local-stack.md)
- [Issue #3](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/3)
