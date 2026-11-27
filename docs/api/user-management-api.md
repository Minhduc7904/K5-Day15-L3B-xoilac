# API quản lý người dùng

Tài liệu này mô tả các endpoint admin dùng để tìm, tạo, sửa, khoá tài khoản học sinh và admin, và đặt lại mật khẩu (issue #20). Người đọc là frontend #9 (màn quản lý người dùng) và backend #11. API này **thay thế** `/api/v1/admin/accounts` của #8. Đăng nhập, phiên và mã lỗi chung nằm ở [API xác thực](auth-api.md).

## Điều kiện gọi

- Base URL: `/api/v1/admin/users`. Local: `http://localhost:8000/api/v1/admin/users`.
- Mọi endpoint cần phiên của một **admin đang active** (cookie `examind_session` hoặc `Authorization: Bearer`). Khách nhận 401 `SESSION_*`, học sinh nhận 403 `FORBIDDEN_ROLE`.
- Body gửi và nhận là JSON. Lỗi nghiệp vụ có dạng `{"detail": "...", "code": "..."}`. Lỗi 422 giữ định dạng mặc định của FastAPI.
- "Xoá" tài khoản là **khoá** (`status = "disabled"`), không xoá dòng, để không vỡ liên kết với đề và lịch sử làm bài (#4, #11).

### Admin gốc

- Admin gốc là tài khoản tạo từ `ADMIN_EMAIL` trong `.env` / `prod.env`, có `is_root = true`. Tối đa một tài khoản; CSDL chặn bằng unique index một phần.
- Không có API nào đặt `is_root`. Gửi trường `is_root` lên API sẽ nhận 422.
- Chỉ admin gốc tạo, sửa, khoá admin khác và đổi vai trò. Cách có admin gốc: xem [backend-auth.md](../architecture/backend-auth.md#cấp-tài-khoản-admin).

## Endpoint và hợp đồng

`UserAdminOut` dùng cho mọi phản hồi trả tài khoản:

```json
{
  "user_id": 4,
  "email": "hs01@example.com",
  "display_name": "Học sinh 01",
  "role": "student",
  "status": "active",
  "is_root": false,
  "created_at": "2026-11-28T09:00:00.000000Z",
  "created_by": 1,
  "last_login_at": "2026-11-28T09:05:00.000000Z"
}
```

`created_by` là admin đã tạo tài khoản qua API; `null` nếu tự đăng ký hoặc do người vận hành tạo. Phản hồi không bao giờ có `password_hash` hay token.

| Method | Path | Việc | Ai gọi được | Thành công |
| --- | --- | --- | --- | --- |
| GET | `/admin/users` | Danh sách, lọc, phân trang | Mọi admin | 200 `UserListOut` |
| GET | `/admin/users/{id}` | Chi tiết | Mọi admin | 200 `UserAdminOut` |
| POST | `/admin/users` | Tạo học sinh hoặc admin | Học sinh: mọi admin. Admin: chỉ admin gốc | 201 `UserAdminOut` |
| PATCH | `/admin/users/{id}` | Sửa `display_name`, `email`, `role`, `status` | Học sinh: mọi admin. Admin: chỉ admin gốc | 200 `UserAdminOut` |
| POST | `/admin/users/{id}/reset-password` | Đặt mật khẩu mới, thu hồi mọi phiên | Như PATCH | 204 |

### GET /admin/users

| Tham số | Kiểu | Mặc định | Ý nghĩa |
| --- | --- | --- | --- |
| `role` | `student` \| `admin` | (tất cả) | Lọc vai trò |
| `status` | `active` \| `disabled` | (tất cả) | Lọc trạng thái |
| `q` | chuỗi ≤ 100 ký tự | (không) | Khớp một phần email hoặc tên hiển thị, không phân biệt hoa thường. `%` và `_` được hiểu là chữ thường |
| `page` | ≥ 1 | 1 | Trang |
| `page_size` | 1–100 | 20 | Số dòng mỗi trang |

```json
// GET /api/v1/admin/users?role=student&q=lop10&page=1&page_size=20 → 200
{"items": [ { "user_id": 4, "email": "lop10_a@example.com", "...": "..." } ], "total": 37, "page": 1, "page_size": 20}
```

Sắp theo `user_id` tăng dần. `total` là tổng số dòng khớp bộ lọc.

### POST /admin/users

```json
// request
{"email": "hs02@example.com", "password": "<mat-khau-moi>", "role": "student", "display_name": "Học sinh 02"}
// 201
{"user_id": 5, "email": "hs02@example.com", "display_name": "Học sinh 02", "role": "student", "status": "active", "is_root": false, "created_at": "...", "created_by": 2, "last_login_at": null}
```

| Trường | Ràng buộc |
| --- | --- |
| `email` | Bắt buộc, `EmailStr`, bỏ khoảng trắng hai đầu, chữ thường, duy nhất không phân biệt hoa thường |
| `password` | Bắt buộc, 8–128 ký tự (cùng hằng `PASSWORD_MIN`/`PASSWORD_MAX` của Auth) |
| `role` | `student` (mặc định) hoặc `admin`. `admin` chỉ admin gốc tạo được |
| `display_name` | Tuỳ chọn, ≤ 100 ký tự |
| Trường khác (vd `is_root`) | 422 |

### PATCH /admin/users/{id}

Chỉ gửi các trường muốn đổi. `display_name: null` hoặc chuỗi rỗng thì xoá tên.

```json
// request
{"status": "disabled"}
// 200: UserAdminOut với status "disabled"
```

| Thay đổi | Tác động thêm |
| --- | --- |
| `status` → `disabled` (khoá) | Thu hồi **mọi** phiên; mọi socket của người đó nhận `session:revoked` `{"reason": "disabled"}` rồi bị ngắt |
| `role` `admin` → `student` (hạ vai trò) | Như trên, `reason` là `role_changed` |
| `status` → `active` (mở khoá) | Người đó phải đăng nhập lại; phiên cũ vẫn đã bị thu hồi |
| `role` `student` → `admin` (chỉ admin gốc) | Không ngắt phiên. Socket đang mở vẫn ở room `role:student` tới khi nối lại |
| `email`, `display_name` | Không ngắt phiên. Email trùng thì 409 |

### POST /admin/users/{id}/reset-password

```json
// request
{"password": "<mat-khau-moi>"}
// 204, không có body
```

Mọi phiên của tài khoản bị thu hồi, mọi socket nhận `session:revoked` `{"reason": "password_reset"}`. Mật khẩu cũ không còn dùng được.

### Ma trận ai được làm gì

Luật nằm trong một hàm thuần `can_manage` (`backend/app/usecase/user_management.py`), có test cho mọi tổ hợp (`tests/test_user_permissions.py`). Xem (GET) thì mọi admin đều được.

| Người làm \ đích | Học sinh | Admin thường khác | Chính mình (admin thường) | Admin gốc |
| --- | --- | --- | --- | --- |
| **Admin gốc** | Mọi việc, kể cả nâng thành admin | Mọi việc: tạo, sửa, khoá, hạ, đặt lại mật khẩu | — | Chỉ tự sửa `display_name`; mọi việc khác 403 `CANNOT_MODIFY_ROOT` |
| **Admin thường** | Tạo, sửa tên/email/trạng thái, khoá, đặt lại mật khẩu. Nâng thành admin: 403 `FORBIDDEN_ROLE` | 403 `FORBIDDEN_ROLE` | Tự khoá hoặc tự hạ: 403 `CANNOT_MODIFY_SELF`. Việc khác: 403 `FORBIDDEN_ROLE` | Sửa tên: 403 `FORBIDDEN_ROLE`. Khoá, hạ, đổi email, đặt lại mật khẩu: 403 `CANNOT_MODIFY_ROOT` |

Tạo tài khoản: admin thường tạo được học sinh; tạo admin thì 403 `FORBIDDEN_ROLE`.

## Lỗi và trường hợp biên

| HTTP | `code` | Khi nào | Frontend nên làm gì |
| --- | --- | --- | --- |
| 422 | (không có) | Email sai, mật khẩu ngoài 8–128 ký tự, `role`/`status` lạ, có trường `is_root` hay trường lạ, `page_size` > 100 | Hiện lỗi ở trường |
| 401 | `SESSION_*` | Mất phiên | Chuyển tới trang đăng nhập |
| 403 | `FORBIDDEN_ROLE` | Người gọi là học sinh; hoặc admin thường đụng tài khoản admin, hoặc nâng học sinh | Ẩn thao tác đó với admin thường |
| 403 | `CANNOT_MODIFY_ROOT` | Khoá, đổi vai trò, đổi email, đặt lại mật khẩu của admin gốc (kể cả chính admin gốc) | Ẩn các thao tác này ở dòng admin gốc |
| 403 | `CANNOT_MODIFY_SELF` | Tự khoá hoặc tự hạ vai trò | Ẩn nút khoá/hạ ở dòng của chính mình |
| 403 | `ACCOUNT_DISABLED` | Tài khoản người gọi vừa bị khoá | Báo tài khoản bị khoá |
| 404 | `USER_NOT_FOUND` | Không có tài khoản với `id` này | Tải lại danh sách |
| 409 | `EMAIL_TAKEN` | Email đã thuộc tài khoản khác (không phân biệt hoa thường) | Hiện lỗi ở trường email |

Hệ thống luôn còn ít nhất một admin, vì admin gốc không khoá hay hạ được. Vì vậy API này không có luật "admin cuối" (`LAST_ADMIN`) như `/admin/accounts` cũ.

## Hướng dẫn mock cho frontend

Dùng tài khoản mock của [auth-api.md](auth-api.md#hướng-dẫn-mock-cho-frontend). Khi mock, coi `admin@example.com` là **admin gốc** (`is_root: true`). Muốn thử giao diện của admin thường thì thêm một admin mock khác với `is_root: false`. Trạng thái giữ trong bộ nhớ.

| Request | Mock trả |
| --- | --- |
| `GET /api/v1/admin/users?...` | 200 `UserListOut`, lọc và phân trang trên mảng trong bộ nhớ |
| `POST /api/v1/admin/users` email mới | 201 `UserAdminOut`, `created_by` = user mock đang đăng nhập |
| `POST` email đã có | 409 `{"detail": "Email này đã được đăng ký", "code": "EMAIL_TAKEN"}` |
| `PATCH` dòng admin gốc với `status`/`role`/`email` | 403 `{"detail": "Không thể khóa, đổi vai trò, đổi email hay đặt lại mật khẩu của admin gốc", "code": "CANNOT_MODIFY_ROOT"}` |
| `PATCH` chính mình `{"status": "disabled"}` | 403 `{"detail": "Không thể tự khóa hoặc tự hạ vai trò của chính mình", "code": "CANNOT_MODIFY_SELF"}` |
| Admin thường `PATCH` dòng admin | 403 `{"detail": "Tài khoản không có quyền dùng chức năng này", "code": "FORBIDDEN_ROLE"}` |
| `GET /api/v1/admin/users/999` | 404 `{"detail": "Không có tài khoản này", "code": "USER_NOT_FOUND"}` |
| `POST /api/v1/admin/users/{id}/reset-password` | 204 |

## Luồng kiểm thử

Đã chạy ngày 2026-11-28 trên PostgreSQL 16 của `docker compose`, backend chạy `uvicorn app.main:asgi_app`. Admin gốc do `ensure_admin` tạo trong `db-init`. Mật khẩu và token đã thay bằng `***`.

```bash
B=http://localhost:8000/api/v1; H="Authorization: Bearer ***"; J='content-type: application/json'
curl -H "$H" "$B/admin/users?role=student&page_size=2"                          # 200 {"items":[...],"total":2,...}
curl -H "$H" -H "$J" -X POST $B/admin/users \
  -d '{"email":"ad2@example.com","password":"***","role":"admin"}'             # 201, created_by 1 (admin gốc)
curl -H "$H" -H "$J" -X PATCH $B/admin/users/1 -d '{"status":"disabled"}'      # 403 CANNOT_MODIFY_ROOT
curl -H "$H" -H "$J" -X PATCH $B/admin/users/1 -d '{"is_root":false}'          # 422 extra_forbidden
curl -H "$H" $B/admin/users/9999                                                # 404 USER_NOT_FOUND
```

Khoá một học sinh đang mở socket: xem kịch bản `scripts/socket_smoke.py` ở [realtime-api.md](realtime-api.md#luồng-kiểm-thử). Học sinh nhận `session:revoked` `{"reason": "disabled"}` ngay (đo được dưới 0,1 s trên máy local).

Test tự động: `cd backend && pytest -q tests/test_user_permissions.py tests/test_user_management_api.py`.

## Tài liệu liên quan

- [Xác thực và phân quyền backend](../architecture/backend-auth.md) (admin gốc, ma trận quyền)
- [API realtime](realtime-api.md) (sự kiện `session:revoked`)
- Mã: `backend/app/api/v1/admin_users.py`, `backend/app/usecase/user_management.py`, `backend/app/schemas/user_admin.py`
