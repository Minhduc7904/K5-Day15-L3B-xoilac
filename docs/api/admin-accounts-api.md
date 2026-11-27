# API quản lý tài khoản admin (đã thay thế)

`/api/v1/admin/accounts` của issue #8 đã được **gỡ ở issue #20** và thay bằng `/api/v1/admin/users`. Xem [API quản lý người dùng](user-management-api.md).

| Cũ (`/admin/accounts`) | Mới (`/admin/users`) |
| --- | --- |
| `GET /admin/accounts` (chỉ danh sách admin) | `GET /admin/users?role=admin` (lọc, tìm, phân trang; xem được cả học sinh) |
| `POST /admin/accounts` kèm `current_password` | `POST /admin/users` với `"role": "admin"`, chỉ admin gốc. Không đòi `current_password` |
| `PATCH /admin/accounts/{id}/status` kèm `current_password` | `PATCH /admin/users/{id}` với `{"status": ...}`. Không đòi `current_password` |
| `REAUTH_FAILED` (401) | Không còn (câu hỏi mở của #20) |
| `LAST_ADMIN` (409) | Không còn: admin gốc không khoá hay hạ được nên luôn còn một admin |
| `CANNOT_MODIFY_SELF` (409) | `CANNOT_MODIFY_SELF` (403) |
| `ACCOUNT_NOT_FOUND` (404) | `USER_NOT_FOUND` (404) |

Trang này được giữ lại để các link cũ (mô tả PR #23, #26) vẫn dẫn tới đúng chỗ.
