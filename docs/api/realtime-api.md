# Kết nối Socket.IO sau đăng nhập

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

Server phát `session:revoked` rồi đóng socket khi phiên hết hạn hoặc bị thu hồi. Đăng xuất thu hồi đúng phiên. Khóa tài khoản, đổi mật khẩu qua luồng quên mật khẩu và thu hồi mọi phiên khi liên kết Google cho tài khoản cũ sẽ đóng mọi socket tương ứng.

## Lỗi và kiểm thử

- API vé trả lỗi xác thực theo [API xác thực](auth-api.md). Handshake từ chối ticket thiếu, hết hạn, đã dùng hoặc trỏ đến phiên không còn hợp lệ.
- Khi mất kết nối, client xin vé mới với khoảng chờ tăng dần. Khi nhận sự kiện thu hồi, client xóa phiên cục bộ và chuyển đến đăng nhập.
- Thử đăng nhập học sinh, xem handshake thành công ngay tại `/profile/setup`, nối thêm tab và đăng xuất. Các tab cùng phiên ngắt, phiên khác vẫn hoạt động.
- Triển khai một tiến trình backend vì registry kết nối và ticket lưu trong bộ nhớ. Khi tăng số tiến trình, cần kho ticket dùng chung và Socket.IO manager dùng chung.

## Tài liệu liên quan

- [API thông báo](notifications-api.md)
- [Deploy backend và nginx](../operations/deploy-backend-ci-cd.md)
- [Issue #36](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/36)
