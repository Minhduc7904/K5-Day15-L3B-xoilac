# API thông báo

Chuông thông báo trên header học sinh đọc danh sách từ API này và nhận thông báo mới theo thời gian thực qua Socket.IO. Thông báo là bản ghi trong bảng `notifications`, do backend tạo khi có sự kiện; frontend không tự tạo.

## Điều kiện gọi

- Gọi HTTP qua `/api/v1` với cookie phiên của học sinh. Khách nhận `401`, admin nhận `403 FORBIDDEN_ROLE`.
- Mỗi người chỉ đọc và sửa thông báo của mình. Thông báo của người khác trả `404 NOTIFICATION_NOT_FOUND`, giống như không tồn tại.
- Phản hồi có `Cache-Control: no-store`.
- Kết nối Socket.IO theo [API realtime](realtime-api.md) để nhận `notification:new`.

## Nguồn thông báo

| `kind` | Khi nào | `link` | Khoá chống trùng |
| --- | --- | --- | --- |
| `attempt_graded` | Lượt làm quá hạn được hệ thống tự nộp và chấm (nộp tay không tạo thông báo) | `/results/online-<id>` | `attempt:<id>:finished` |
| `draft_ready` | Dựng xong một đề nháp **mới** của phiên chat. Sửa đề tại chỗ không tạo thêm | `/exams/draft-<id>` | `draft:<id>` |
| `credit_granted` | Job hằng ngày cộng credit và số cộng lớn hơn 0 | `/profile#credit` | `credit:<ngày>` |
| `study_reminder` | Lịch nhắc học được gửi thành công | `/dashboard` | `reminder:<ngày>` |

Mỗi cặp `(user_id, dedupe_key)` chỉ có một thông báo, nên worker chạy lại hoặc gửi lại không tạo bản trùng. Thông báo được ghi trong cùng giao dịch với nghiệp vụ sinh ra nó.

## Endpoint và hợp đồng

### `GET /student/me/notifications`

| Tham số query | Ý nghĩa |
| --- | --- |
| `limit` | 1–50, mặc định 20 |
| `before_id` | Chỉ lấy thông báo có `id` nhỏ hơn giá trị này, để tải trang tiếp theo |

Trả `200`:

```json
{
  "items": [
    {"id": 31, "kind": "draft_ready", "title": "Đề nháp đã sẵn sàng", "body": "Ôn hàm số: 20 câu.",
     "link": "/exams/draft-42", "created_at": "2026-11-28T08:15:02Z", "read_at": null}
  ],
  "unread": 3,
  "next_before_id": null
}
```

`items` sắp mới nhất trước. `unread` là tổng số chưa đọc của tài khoản, không chỉ trong trang này. `next_before_id` khác `null` khi còn trang cũ hơn.

### `POST /student/me/notifications/{id}/read`

Đánh dấu một thông báo đã đọc. Gọi lại là vô hại. Trả `204`, hoặc `404 NOTIFICATION_NOT_FOUND`.

### `POST /student/me/notifications/read-all`

Đánh dấu mọi thông báo chưa đọc là đã đọc. Trả `204`.

### Sự kiện Socket.IO `notification:new`

Khi có thông báo mới, server phát sự kiện này vào room `user:{id}` với payload giống một phần tử `items`. Worker chạy ở tiến trình riêng nên chỉ ghi vào cơ sở dữ liệu; tiến trình API kiểm tra thông báo mới khoảng mỗi 2 giây cho các học sinh đang kết nối rồi phát. Client có thể lỡ sự kiện (mất mạng, tab nền), nên frontend tải lại danh sách khi kết nối lại và khi tab hiện lại.

## Lỗi và trường hợp biên

| Mã | Điều kiện |
| --- | --- |
| `401 SESSION_*` | Chưa đăng nhập hoặc phiên không còn dùng được |
| `403 FORBIDDEN_ROLE` | Tài khoản không phải học sinh |
| `404 NOTIFICATION_NOT_FOUND` | ID không tồn tại hoặc thuộc người khác |
| `422` | `limit` ngoài 1–50 hoặc `before_id` không dương |

## Luồng kiểm thử

```powershell
cd backend; pytest -q tests/test_notifications.py
```

Bộ kiểm thử phủ: danh sách, đánh dấu đã đọc và quyền sở hữu (người khác nhận 404), bốn nguồn sinh thông báo kèm kiểm tra không sinh trùng, và watcher chỉ đẩy thông báo mới cho đúng chủ đang kết nối. Phân trang bằng `before_id` chưa có kiểm thử riêng.

Kiểm tay với local stack ([run-local-stack.md](../operations/run-local-stack.md)): đăng nhập học sinh, tạo và dựng một đề từ chat. Chuông hiện số 1 mà không cần tải lại trang; bấm vào mở `/exams/draft-<id>` và số chưa đọc về 0. Mở bài có giờ, đóng tab tới sau hạn, mở lại: có thông báo "đã tự động nộp và chấm".

## Tài liệu liên quan

- [API realtime](realtime-api.md)
- [Trang học sinh frontend](../architecture/frontend-student-pages.md)
- Mã: `backend/app/usecase/notifications.py`, `backend/app/api/v1/notifications.py`, `backend/app/api/realtime.py`, migration `0016_notifications`
