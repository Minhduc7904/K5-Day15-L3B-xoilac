# API nhập đề PDF

Hợp đồng dự kiến cho backend, frontend admin và kiểm thử Issue #3.

## Điều kiện gọi

Base URL local là `http://localhost:8000/api/v1`. Các thao tác nhập và duyệt dùng phiên có vai trò admin theo API Auth của backend. URL xem đối tượng đã ký hết hạn sau 5 phút hoặc khi backend khởi động lại.

## Endpoint và hợp đồng

| Method và path tương đối | Kết quả |
| --- | --- |
| `POST /admin/pdf-imports` | Multipart `file`, trả `202` với mã phiên, trạng thái và URL theo dõi. |
| `GET /admin/pdf-imports` | Danh sách phiên với `offset` và `limit`. |
| `GET /admin/pdf-imports/{import_id}` | Trạng thái, bước lỗi, cảnh báo, mã PDF gốc và số câu nháp. |
| `GET /admin/pdf-imports/{import_id}/drafts` | Danh sách bản nháp theo thứ tự nguồn. |
| `GET /admin/pdf-imports/{import_id}/drafts/{draft_id}` | Nội dung, đáp án, lời giải, nguồn, hình và nhãn gợi ý. |
| `PATCH /admin/pdf-imports/{import_id}/drafts/{draft_id}` | Lưu các trường admin đã sửa và trả bản nháp hiện tại. |
| `POST /admin/pdf-imports/{import_id}/drafts/{draft_id}/approve` | Xuất bản một lần, trả `questionId`. |
| `POST /admin/pdf-imports/{import_id}/drafts/{draft_id}/reject` | Ghi trạng thái bỏ bản nháp. |
| `GET /admin/pdf-imports/{import_id}/media/{media_id}/url` | Trả URL xem PDF hoặc hình có thời hạn. |

Ví dụ phản hồi tải lên

```json
{"id":1,"status":"queued","stage":"upload","statusUrl":"/api/v1/admin/pdf-imports/1"}
```

## Lỗi và trường hợp biên

| Mã | Điều kiện |
| --- | --- |
| 401 | Thiếu phiên hoặc phiên không còn hợp lệ. |
| 403 | Tài khoản thiếu quyền admin hoặc URL xem tệp hết hạn. |
| 404 | Phiên, câu hoặc hình không tồn tại trong phạm vi yêu cầu. |
| 409 | Bản nháp đã có quyết định hoặc phiên chưa sẵn sàng. |
| 413 | PDF vượt giới hạn. |
| 415 | Đầu vào không phải PDF. |
| 422 | PDF không đọc được hoặc câu chưa đạt điều kiện duyệt. |
| 503 | Backend chưa cấu hình nhà cung cấp. |

Lỗi xử lý sau `202` nằm trong chi tiết phiên. Câu có đáp án chưa xác định hoặc hình bắt buộc bị thiếu cần được sửa trước khi duyệt.

## Luồng kiểm thử

1. Tải PDF, dùng mã phiên để theo dõi đến `ready_for_review`.
2. Mở bản nháp Phần I câu 6 của mẫu, kiểm thứ tự A–D và dùng URL xem từng hình. Đối chiếu đáp án D với trang 7.
3. Chốt chương và độ khó, duyệt câu, rồi dùng mã câu trả về để kiểm bản đọc chung chỉ chứa nội dung, lựa chọn có thứ tự và tham chiếu ảnh.
4. Duyệt một câu có đáp án mâu thuẫn hoặc thiếu hình để kiểm API trả `422`.

## Tài liệu liên quan

- [Pipeline nhập đề PDF](pipeline.md)
- [API mẫu](../../api/sample-api.md)
- [Issue #4](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/4)
