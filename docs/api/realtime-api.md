# API realtime (Socket.IO)

Tài liệu này mô tả cách client nối kênh Socket.IO của Examind, các room, sự kiện server gửi và API thống kê học sinh online (issue #20). Người đọc là frontend #9 và backend cần phát tin theo vai trò. Kiến trúc và lý do thiết kế nằm ở [backend-realtime.md](../architecture/backend-realtime.md).

## Điều kiện gọi

- **Đường dẫn:** Socket.IO (protocol v5, Engine.IO v4) tại `socketio_path = "/api/socket.io"` trên cùng host với API: local `http://localhost:8000`, prod `https://examind.duckdns.org` (WSS, cần cổng 443 mở, xem [deploy-backend-ci-cd.md](../operations/deploy-backend-ci-cd.md#socket-và-wss)).
- **Frontend nối thẳng backend** qua biến `NEXT_PUBLIC_SOCKET_URL`, không đi qua Vercel rewrites, vì rewrites không chuyển WebSocket.
- **Origin** của trang phải nằm trong `CORS_ORIGINS` của backend. `CORS_ORIGINS` trống thì chỉ cùng origin được nối.
- **Xác thực bằng ticket, không bằng cookie:** trang ở origin khác backend nên cookie phiên không đi theo handshake WebSocket.
- Backend chạy **một worker**; xem ràng buộc ở [backend-realtime.md](../architecture/backend-realtime.md#ràng-buộc-một-worker).

## Endpoint và hợp đồng

### 1. Xin ticket: POST /api/v1/auth/socket-ticket

Cần phiên (cookie hoặc Bearer). Không có body.

```json
// 200 (Cache-Control: no-store)
{"ticket": "u8m3...", "expires_in": 30}
```

- Ticket ngẫu nhiên, sống `expires_in` giây (mặc định 30, biến `SOCKET_TICKET_TTL_SECONDS`), **dùng một lần**.
- Ticket gắn với người dùng **và phiên** đã xin. Đăng xuất phiên đó thì socket mở bằng ticket của nó bị ngắt.
- Thiếu phiên: 401 `SESSION_*` như mọi endpoint cần phiên.
- Mỗi lần nối (kể cả nối lại sau khi rớt mạng) cần một ticket **mới**.

### 2. Nối socket

```ts
import { io } from "socket.io-client";

const { ticket } = (await api.post("/auth/socket-ticket")).data;
const socket = io(process.env.NEXT_PUBLIC_SOCKET_URL, {
  path: "/api/socket.io",
  transports: ["websocket"],
  auth: { ticket },
  reconnection: false, // nối lại thì xin ticket mới rồi gọi io(...) lại
});
socket.on("connect_error", (err) => console.warn(err.message, err.data?.code));
socket.on("session:revoked", ({ reason }) => { socket.disconnect(); /* xoá user khỏi store, về /login */ });
```

Python (dùng trong `scripts/socket_smoke.py`):

```python
client = socketio.AsyncClient(reconnection=False)
await client.connect(base, socketio_path="/api/socket.io", transports=["websocket"], auth={"ticket": ticket})
```

### 3. Room

Server tự đưa kết nối vào room sau khi xác thực; client không tự vào hay rời room.

| Room | Ai vào | Dùng để |
| --- | --- | --- |
| `role:student` | Mọi học sinh | Phát tin cho học sinh; đếm online |
| `role:admin` | Mọi admin | Phát tin cho admin |
| `user:{id}` | Chính người đó | Gửi riêng |

Tên room chỉ sinh ở `backend/app/api/socket/rooms.py` (`role_room`, `user_room`).

### 4. Sự kiện server → client

| Sự kiện | Payload | Khi nào | Sau đó |
| --- | --- | --- | --- |
| `session:revoked` | `{"reason": "logout" \| "disabled" \| "password_reset" \| "role_changed" \| "expired"}` | Phiên hoặc tài khoản bị thu hồi (bảng dưới) | Server ngắt kết nối ngay |

| `reason` | Nguồn | Kết nối nào bị ngắt |
| --- | --- | --- |
| `logout` | `POST /auth/logout` | Chỉ các kết nối mở bằng ticket của **phiên vừa đăng xuất**. Tab của phiên khác (thiết bị khác) giữ nguyên |
| `disabled` | Admin khoá tài khoản (`PATCH /admin/users/{id}` `status=disabled`) | Mọi kết nối của người đó |
| `password_reset` | `POST /admin/users/{id}/reset-password` | Mọi kết nối của người đó |
| `role_changed` | Admin hạ vai trò admin → student | Mọi kết nối của người đó |
| `expired` | Dự phòng; hiện server chưa gửi (xem "Chưa làm" ở [backend-realtime.md](../architecture/backend-realtime.md#chưa-làm)) | — |

### 5. Thống kê online: GET /api/v1/admin/stats/online-students

Chỉ admin (học sinh 403 `FORBIDDEN_ROLE`, khách 401 `SESSION_MISSING`).

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

- `online_students`: số học sinh có ít nhất một kết nối sống. Nhiều tab chỉ tính một học sinh; `connections` cộng đủ số kết nối. Admin không được tính.
- `as_of`: thời điểm đọc, ISO 8601 UTC.
- `users` sắp theo `user_id`, phân trang bằng `page` (≥ 1) và `page_size` (1–100). `include` khác `users` thì 422.

## Lỗi và trường hợp biên

**Từ chối kết nối.** Client nhận sự kiện `connect_error` với `err.message` là câu tiếng Việt và `err.data = {"code": ...}`:

| `code` | Khi nào |
| --- | --- |
| `TICKET_MISSING` | Không gửi `auth.ticket`, hoặc ticket rỗng hay không phải chuỗi |
| `TICKET_INVALID` | Ticket lạ, đã dùng, hoặc quá `expires_in` giây |
| `SESSION_REVOKED` / `SESSION_EXPIRED` / `SESSION_INVALID` | Phiên gắn với ticket đã bị thu hồi, hết hạn hoặc không còn |
| `ACCOUNT_DISABLED` | Tài khoản bị khoá sau khi xin ticket |

Gặp các mã trên thì không thử lại với cùng ticket. Mã `SESSION_*` và `ACCOUNT_DISABLED` nghĩa là phải đăng nhập lại.

**Mất mạng.** Server dùng ping/pong mặc định của Socket.IO (`pingInterval` 25 s, `pingTimeout` 20 s). Client mất mạng bị coi là ngắt sau tối đa khoảng 45 s; lúc đó thống kê online mới giảm. Đóng tab hay `socket.disconnect()` thì giảm ngay.

**Thay đổi sau khi đã nối.** Socket chỉ được kiểm phiên lúc nối. Thu hồi phiên qua đăng xuất, khoá, đặt lại mật khẩu hay hạ vai trò đều chủ động ngắt socket. Phiên tự hết hạn khi đang nối thì socket chưa bị ngắt.

## Luồng kiểm thử

Đã chạy ngày 2026-11-28 trên PostgreSQL 16 của `docker compose`, backend `uvicorn app.main:asgi_app --workers 1`:

```text
$ SMOKE_ADMIN_EMAIL=admin@example.com SMOKE_ADMIN_PASSWORD=*** python scripts/socket_smoke.py --base http://127.0.0.1:8008
Thống kê trước kịch bản: 0 học sinh, 0 kết nối
[ĐẠT] A mở 2 kết nối, B mở 1 - thống kê 2 học sinh, 3 kết nối
[ĐẠT] Đóng 2 kết nối của A - thống kê 1 học sinh, 1 kết nối
[ĐẠT] Dùng lại ticket đã dùng - bị từ chối, code=TICKET_INVALID
[ĐẠT] Admin khoá B - PATCH 200; B nhận [{'reason': 'disabled'}] sau 0.00 s; thống kê 0 học sinh, 0 kết nối
[ĐẠT] A đăng xuất - logout 204; A nhận [{'reason': 'logout'}] sau 0.00 s
Kết quả: 5/5 bước đạt
```

Test tự động (không cần Docker): `cd backend && pytest -q tests/test_realtime_units.py tests/test_realtime_api.py tests/test_admin_stats_api.py tests/test_socket_integration.py`. `test_socket_integration.py` chạy uvicorn thật trên cổng tạm và nối bằng `socketio.AsyncClient`.

## Tài liệu liên quan

- [Kiến trúc realtime](../architecture/backend-realtime.md)
- [API quản lý người dùng](user-management-api.md) · [API xác thực](auth-api.md)
- Mã: `backend/app/api/socket/`, `backend/app/usecase/realtime.py`, `backend/app/api/v1/admin_stats.py`
