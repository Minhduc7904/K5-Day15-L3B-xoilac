# Kết nối Socket.IO sau đăng nhập

Tài liệu này mô tả cách client nối kênh Socket.IO của Examind, các room, sự kiện server gửi, và API thống kê học sinh online của admin (#20). Người đọc là frontend và backend cần phát tin theo vai trò. Mã: `backend/app/api/realtime.py`. Kiến trúc: [backend-realtime.md](../architecture/backend-realtime.md).

## Điều kiện gọi

Frontend gọi API ticket cùng origin qua Next.js rewrite và dùng cookie phiên. Sau đó kết nối trực tiếp tới backend qua WebSocket. Đặt `NEXT_PUBLIC_SOCKET_URL` bằng origin backend, ví dụ `https://examind.duckdns.org`. Đường dẫn Socket.IO cố định là `/api/socket.io`. Thêm origin của frontend vào `CORS_ORIGINS`.

## Ticket, room và sự kiện

`POST /api/v1/auth/socket-ticket` trả `{ "ticket": "<mã>", "expires_in": 30 }` và header `Cache-Control: no-store`. Gửi `auth: { ticket }` khi mở namespace mặc định. Mỗi ticket chỉ đổi được một lần. Backend kiểm lại thời hạn, trạng thái phiên và quyền tài khoản khi nối.

| Room | Thành viên |
| --- | --- |
| `role:student` | Các kết nối của học sinh |
| `role:admin` | Các kết nối của admin |
| `user:{id}` | Các kết nối của tài khoản đó |
| `attempt:{id}` | Các tab đã xác minh thuộc học sinh sở hữu lượt làm. Xem [API làm bài online](online-exam-attempts-api.md#room-socketio). |

### Sự kiện `notification:new`

Server phát vào room `user:{id}` khi học sinh có thông báo mới (bài hết giờ đã tự chấm, đề nháp dựng xong, cộng credit hằng ngày, nhắc lịch học). Payload là một thông báo như phần tử `items` của [API thông báo](notifications-api.md): `id`, `kind`, `title`, `body`, `link`, `created_at`, `read_at`. Worker chạy ở tiến trình riêng nên chỉ ghi cơ sở dữ liệu; tiến trình API kiểm tra thông báo mới khoảng mỗi 2 giây cho các học sinh đang kết nối. Client có thể lỡ sự kiện lúc mất mạng, nên tải lại danh sách qua HTTP khi kết nối lại.

Server quyết định room từ dữ liệu phiên. Frontend mở một kết nối mỗi tab sau khi đăng nhập hoặc khôi phục phiên. Chuyển giữa hoàn tất hồ sơ và onboarding tour giữ kết nối đang mở.

### Sự kiện `session:revoked`

Server phát `session:revoked` rồi đóng socket khi phiên hết hạn hoặc bị thu hồi. Từ #20, sự kiện kèm payload `{"reason": ...}` khi server biết lý do, để frontend hiện đúng thông báo. Client cũ không đọc payload vẫn chạy như trước.

| `reason` | Nguồn | Kết nối nào bị đóng |
| --- | --- | --- |
| `logout` | `POST /auth/logout` | Chỉ các kết nối mở bằng ticket của **phiên vừa đăng xuất**. Phiên khác (thiết bị khác) giữ nguyên |
| `disabled` | Admin khoá tài khoản: `PATCH /admin/users/{id}` với `status=disabled` ([user-management-api.md](user-management-api.md)) | Mọi kết nối của người đó |
| `password_reset` | Admin đặt lại mật khẩu (`POST /admin/users/{id}/reset-password`), hoặc học sinh tự đặt lại qua luồng quên mật khẩu | Mọi kết nối của người đó |
| `role_changed` | Admin gốc hạ admin thành student | Mọi kết nối của người đó |
| `expired` | Phiên tới `expires_at` trong lúc đang nối (server hẹn giờ khi nối) | Kết nối đó |
| (không có payload) | Liên kết Google cho tài khoản cũ chưa xác minh email | Mọi kết nối của người đó |

## Thống kê online: GET /api/v1/admin/stats/online-students

Chỉ admin (học sinh 403 `FORBIDDEN_ROLE`, khách 401 `SESSION_MISSING`). Đọc trực tiếp registry kết nối của tiến trình API (#20).

```json
// GET /api/v1/admin/stats/online-students → 200
{"online_students": 12, "connections": 15, "as_of": "2026-11-28T09:30:00.123456Z"}

// GET /api/v1/admin/stats/online-students?include=users&page=1&page_size=20 → 200
{
  "online_students": 12, "connections": 15, "as_of": "2026-11-28T09:30:00.123456Z",
  "users": [{"user_id": 4, "display_name": "Học sinh 01", "email": "hs01@example.com", "connections": 2}],
  "page": 1, "page_size": 20
}
```

- `online_students`: số học sinh có ít nhất một kết nối đang mở. Nhiều tab chỉ tính một học sinh; `connections` cộng đủ số kết nối. Admin không được tính.
- `as_of`: thời điểm đọc, ISO 8601 UTC.
- `users` sắp theo `user_id`, phân trang bằng `page` (≥ 1) và `page_size` (1–100). `include` khác `users` thì 422.
- Kết nối "đang mở" do ping/pong mặc định của Socket.IO quyết định (`pingInterval` 25 s, `pingTimeout` 20 s): client mất mạng bị tính là ngắt sau tối đa khoảng 45 s. Đóng tab thì giảm ngay.

## Lỗi và kiểm thử

- API vé trả lỗi xác thực theo [API xác thực](auth-api.md). Handshake từ chối ticket thiếu, hết hạn, đã dùng hoặc trỏ đến phiên không còn hợp lệ. Client nhận `connect_error` với thông báo chung `Connection rejected by server`, **không có mã lỗi riêng** cho từng trường hợp.
- Khi mất kết nối, client xin vé mới với khoảng chờ tăng dần. Khi nhận sự kiện thu hồi, client xóa phiên cục bộ và chuyển đến đăng nhập.
- Thử đăng nhập học sinh, xem handshake thành công ngay tại `/profile/setup`, nối thêm tab và đăng xuất. Các tab cùng phiên ngắt, phiên khác vẫn hoạt động.
- Triển khai một tiến trình backend vì registry kết nối và ticket lưu trong bộ nhớ (`--workers 1` trong Dockerfile). Khi tăng số tiến trình, cần kho ticket dùng chung và Socket.IO manager dùng chung.
- Kịch bản #20 (hai tab, đóng tab, dùng lại ticket, admin khoá, đăng xuất): trong `backend/`, chạy `SMOKE_ADMIN_EMAIL=... SMOKE_ADMIN_PASSWORD=... python scripts/socket_smoke.py --base http://localhost:8000` với backend đang chạy; kết quả mong đợi `5/5 bước đạt`.

## Tài liệu liên quan

- [API thông báo](notifications-api.md) · [API quản lý người dùng](user-management-api.md)
- [Kiến trúc realtime](../architecture/backend-realtime.md)
- [Deploy backend và nginx](../operations/deploy-backend-ci-cd.md)
- [Issue #36](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/36), [Issue #20](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/20)
