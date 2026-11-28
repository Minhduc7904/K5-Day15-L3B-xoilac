# API quản lý tài khoản admin

Tài liệu này mô tả cách một admin đã đăng nhập xem danh sách admin, tạo admin mới, và khoá hoặc mở khoá admin khác. Người đọc là frontend #9 (trang quản trị) và backend #11. Đăng nhập, phiên và mã lỗi chung nằm ở [API xác thực](auth-api.md); luật cấp quyền admin nằm ở [backend-auth.md](../architecture/backend-auth.md#cấp-tài-khoản-admin).

## Điều kiện gọi

- Base URL: `/api/v1/admin/accounts`. Local là `http://localhost:8000/api/v1/admin/accounts`.
- Mọi endpoint cần phiên của một **admin đang active** (cookie `examind_session` hoặc `Authorization: Bearer`, như [auth-api.md](auth-api.md#điều-kiện-gọi)). Khách nhận 401 `SESSION_*`, student nhận 403 `FORBIDDEN_ROLE`.
- Thao tác cấp hoặc đổi quyền (`POST`, `PATCH`) đòi thêm `current_password`, tức mật khẩu của chính admin đang thao tác. Nhờ vậy, kẻ chiếm được phiên (vd máy để quên chưa đăng xuất) vẫn không tạo hay khoá được admin.
- Body gửi và nhận là JSON. Lỗi nghiệp vụ có dạng `{"detail": "...", "code": "..."}`. Lỗi 422 của FastAPI giữ định dạng mặc định.
- API này không quản lý tài khoản student, chỉ quản lý admin.

## Endpoint và hợp đồng

`AdminAccountOut` dùng cho mọi phản hồi:

```json
{
  "user_id": 2,
  "email": "admin2@example.com",
  "display_name": "Admin 2",
  "status": "active",
  "created_at": "2026-11-27T17:14:27.032724Z",
  "created_by": 1,
  "last_login_at": null
}
```

- `created_by`: `user_id` của admin đã tạo tài khoản này qua API. Giá trị là `null` nếu tài khoản do người vận hành tạo (`ensure_admin` lúc khởi động hoặc `create_admin` cứu hộ).
- `status`: `active` hoặc `disabled`.
- Không bao giờ có `password_hash` hay token.

### GET /admin/accounts

Trả danh sách mọi tài khoản admin, kể cả tài khoản đã khoá, sắp theo `user_id`.

```json
// 200
[
  {"user_id": 1, "email": "admin@example.com", "display_name": "Quản trị", "status": "active", "created_at": "2026-11-27T17:13:13.203823Z", "created_by": null, "last_login_at": "2026-11-27T17:14:26.779893Z"},
  {"user_id": 2, "email": "admin2@example.com", "display_name": "Admin 2", "status": "active", "created_at": "2026-11-27T17:14:27.032724Z", "created_by": 1, "last_login_at": "2026-11-27T17:14:27.573713Z"}
]
```

### POST /admin/accounts

Tạo một admin mới. `created_by` được ghi là admin đang thao tác.

```json
// request
{"email": "admin2@example.com", "password": "<mat-khau-admin-moi>", "display_name": "Admin 2", "current_password": "<mat-khau-cua-ban>"}
// 201
{"user_id": 2, "email": "admin2@example.com", "display_name": "Admin 2", "status": "active", "created_at": "2026-11-27T17:14:27.032724Z", "created_by": 1, "last_login_at": null}
```

| Trường | Ràng buộc |
| --- | --- |
| `email` | Bắt buộc, cùng luật với đăng ký: `EmailStr`, bỏ khoảng trắng, chữ thường, tối đa 255 ký tự, duy nhất không phân biệt hoa thường |
| `password` | Bắt buộc, 8–128 ký tự |
| `display_name` | Tuỳ chọn, tối đa 100 ký tự |
| `current_password` | Bắt buộc, mật khẩu của admin đang thao tác |

Email đã có, **kể cả của một student**, sẽ nhận 409 `EMAIL_TAKEN`. API không bao giờ nâng student thành admin.

### PATCH /admin/accounts/{user_id}/status

Khoá (`disabled`) hoặc mở khoá (`active`) một admin khác.

```json
// request
{"status": "disabled", "current_password": "<mat-khau-cua-ban>"}
// 200
{"user_id": 2, "email": "admin2@example.com", "display_name": "Admin 2", "status": "disabled", "created_at": "2026-11-27T17:14:27.032724Z", "created_by": 1, "last_login_at": "2026-11-27T17:14:27.573713Z"}
```

- **Khoá:** mọi phiên đang mở của tài khoản đó bị thu hồi ngay, nên request tiếp theo của họ nhận 401 `SESSION_REVOKED`. Họ cũng không đăng nhập được nữa, vì đăng nhập sẽ trả 403 `ACCOUNT_DISABLED`.
- **Mở khoá:** họ phải đăng nhập lại, các phiên cũ vẫn đã bị thu hồi.
- Đặt đúng trạng thái hiện có (vd khoá một tài khoản đã khoá) thì trả 200 và không đổi gì.

Thứ tự kiểm: mật khẩu xác nhận → tài khoản đích là admin → (khi khoá) không phải admin active cuối cùng → không phải chính mình. Vì vậy, khi bạn là admin active duy nhất mà thử tự khoá, kết quả là `LAST_ADMIN`; khi còn admin active khác thì là `CANNOT_MODIFY_SELF`.

## Lỗi và trường hợp biên

| HTTP | `code` | Khi nào | Frontend nên làm gì |
| --- | --- | --- | --- |
| 422 | (không có) | Email sai, mật khẩu ngoài 8–128 ký tự, thiếu `current_password`, `status` khác `active`/`disabled` | Hiện lỗi ở trường |
| 401 | `REAUTH_FAILED` | `current_password` sai. Không có gì thay đổi | Báo "Mật khẩu xác nhận không đúng". **Giữ phiên, không chuyển tới trang đăng nhập** |
| 401 | `SESSION_MISSING` / `SESSION_INVALID` / `SESSION_EXPIRED` / `SESSION_REVOKED` | Mất phiên (xem [auth-api.md](auth-api.md#lỗi-và-trường-hợp-biên)) | Chuyển tới trang đăng nhập |
| 403 | `FORBIDDEN_ROLE` | Người gọi là student | Báo không có quyền |
| 403 | `ACCOUNT_DISABLED` | Tài khoản người gọi vừa bị khoá | Báo tài khoản bị khoá |
| 404 | `ACCOUNT_NOT_FOUND` | `user_id` không tồn tại hoặc không phải admin | Tải lại danh sách |
| 409 | `EMAIL_TAKEN` | Email đã có tài khoản (admin hoặc student) | Hiện lỗi ở trường email |
| 409 | `CANNOT_MODIFY_SELF` | Đổi trạng thái của chính mình | Ẩn nút khoá ở dòng của chính mình |
| 409 | `LAST_ADMIN` | Khoá admin active cuối cùng | Báo phải còn ít nhất một admin hoạt động |

`REAUTH_FAILED` cũng là 401, nên frontend phải phân nhánh theo `code`, không theo mã HTTP. Chỉ các mã `SESSION_*` mới có nghĩa là mất phiên.

**Hai admin khoá lẫn nhau cùng lúc:** request đến sau phải chờ khoá dòng (`SELECT ... FOR UPDATE` trên các dòng admin), sau đó thấy chỉ còn một admin active và nhận 409 `LAST_ADMIN`. Hệ thống luôn còn ít nhất một admin active.

**Chưa làm:** hạ admin thành student, xoá tài khoản, admin đặt lại mật khẩu cho người khác, khoá hoặc mở khoá tài khoản student, giới hạn số lần nhập sai `current_password`. Xem [backend-auth.md](../architecture/backend-auth.md#chưa-làm).

## Gợi ý giao diện

Hộp thoại tạo admin, khoá và mở khoá đều có ô "Mật khẩu của bạn"; ẩn nút khoá ở dòng của chính mình; hiện `created_by` bằng email tra từ cùng danh sách.

## Luồng kiểm thử

Đã chạy ngày 2026-11-28 trên Windows 11 bằng `docker compose up -d` (PostgreSQL 16, MinIO). Backend chạy bằng uvicorn trỏ vào stack đó, `ADMIN_*` đặt trong `.env`. Mật khẩu và token đã thay bằng `***`. A là admin mặc định (`user_id=1`, do `ensure_admin` tạo), B là admin thứ hai.

```bash
B=http://localhost:8000/api/v1; J='content-type: application/json'
curl -s -i -c a.txt -b a.txt -X POST $B/auth/login -H "$J" -d '{"email":"admin@example.com","password":"***"}'   # 200, role admin
curl -s -i -c a.txt -b a.txt -X POST $B/admin/accounts -H "$J" \
  -d '{"email":"admin2@example.com","password":"***","display_name":"Admin 2","current_password":"***"}'          # 201, created_by 1
curl -s -i -c b.txt -b b.txt -X POST $B/auth/login -H "$J" -d '{"email":"admin2@example.com","password":"***"}'   # 200
curl -s -i -c b.txt -b b.txt -X PATCH $B/admin/accounts/1/status -H "$J" -d '{"status":"disabled","current_password":"***"}'  # 200, B khoá A
curl -s -i -c a.txt -b a.txt $B/admin/accounts                                                                    # 401 SESSION_REVOKED
curl -s -i -c b.txt -b b.txt -X PATCH $B/admin/accounts/1/status -H "$J" -d '{"status":"active","current_password":"***"}'    # 200, B mở khoá A
curl -s -i -c a.txt -b a.txt -X POST $B/auth/login -H "$J" -d '{"email":"admin@example.com","password":"***"}'   # 200, A đăng nhập lại
curl -s -i -c a.txt -b a.txt -X PATCH $B/admin/accounts/2/status -H "$J" -d '{"status":"disabled","current_password":"***"}'  # 200, A khoá B
curl -s -i -c a.txt -b a.txt -X PATCH $B/admin/accounts/1/status -H "$J" -d '{"status":"disabled","current_password":"***"}'  # 409 LAST_ADMIN
```

Các ca khác đã kiểm cùng ngày:

| Thao tác | Kết quả |
| --- | --- |
| Tạo admin với `current_password` sai | 401 `REAUTH_FAILED`, không tạo gì, phiên vẫn còn |
| Đăng nhập A khi đang bị khoá | 403 `ACCOUNT_DISABLED` |
| B tự khoá khi A đã bị khoá (B là admin active duy nhất) | 409 `LAST_ADMIN` |
| B tự khoá khi cả A và B đều active | 409 `CANNOT_MODIFY_SELF` |
| Student gọi `GET /admin/accounts` | 403 `FORBIDDEN_ROLE` |
| Một phiên `psql` giữ `FOR UPDATE` các dòng admin trong 3 giây, cùng lúc A khoá B và B khoá A | Một request 200, request kia 409 `LAST_ADMIN`; sau đó `1:active 2:disabled` |
| Đối chứng: cùng kịch bản nhưng tạm bỏ `with_for_update()` | Cả hai 200, sau đó `1:disabled 2:disabled`, tức không còn admin nào. Đây là lý do phải khoá dòng |
| Cứu hộ sau ca đối chứng: `create_admin --email rescue@example.com`, đăng nhập, mở khoá A | 200; A active trở lại |

Test tự động: `cd backend && pytest -q tests/test_admin_accounts.py`. SQLite không có khoá dòng, nên ca đồng thời chỉ kiểm được thủ công trên PostgreSQL như trên.

## Tài liệu liên quan

- [Xác thực và phân quyền backend](../architecture/backend-auth.md#cấp-tài-khoản-admin)
- [API xác thực](auth-api.md)
- [Chạy bộ khung local](../operations/run-local-stack.md) (admin mặc định, cứu hộ)
- Mã: `backend/app/api/v1/admin_accounts.py`, `backend/app/usecase/admin_accounts.py`
