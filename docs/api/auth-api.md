# API xác thực

Tài liệu này mô tả các endpoint đăng ký, đăng nhập, đăng xuất và lấy người dùng hiện tại của issue #8, cùng endpoint admin mẫu. Người đọc là frontend #9 (gọi và mock API) và backend #3, #4, #5, #11 (áp dụng quyền). Cơ chế bên trong nằm ở [backend-auth.md](../architecture/backend-auth.md). Tạo và quản lý tài khoản admin nằm ở [API quản lý tài khoản admin](admin-accounts-api.md).

## Điều kiện gọi

- Base URL local: `http://localhost:8000/api/v1`. Qua frontend thì dùng đường dẫn tương đối `/api/v1/...`, Next.js rewrites chuyển tiếp sang backend. Tài liệu tự sinh ở `/docs`.
- Body gửi và nhận dạng JSON (`content-type: application/json`).
- **Phiên** nằm trong cookie `examind_session` với các thuộc tính `HttpOnly; SameSite=Lax; Path=/`, thêm `Secure` khi `COOKIE_SECURE=true`. Hạn của cookie là `SESSION_TTL_HOURS` giờ, mặc định 168.
  - Trình duyệt: cookie đi kèm tự động khi gọi cùng origin. Với Axios trong cùng origin không cần cấu hình thêm. Chỉ khi dev gọi thẳng backend khác origin mới cần `withCredentials: true` và đặt `CORS_ORIGINS` ở backend.
  - curl hoặc Swagger: gửi `Authorization: Bearer <token>`. Token lấy từ header `set-cookie` khi đăng nhập. Nếu request có cả hai thì cookie được dùng.
- Token không bao giờ nằm trong body. JavaScript không đọc được cookie, nên frontend biết trạng thái đăng nhập bằng cách gọi `GET /auth/me`.

## Endpoint và hợp đồng

`UserOut` dùng chung cho mọi phản hồi trả người dùng:

```json
{
  "user_id": 1,
  "email": "hs01@example.com",
  "role": "student",
  "status": "active",
  "display_name": null,
  "created_at": "2026-11-27T15:52:23.845134Z"
}
```

`role` là `student` hoặc `admin`. `status` là `active` hoặc `disabled`. Phản hồi không bao giờ chứa `password_hash` hay token.

### POST /auth/register

Công khai. Gửi mã OTP 6 số. Tạo tài khoản học sinh và phiên sau khi OTP được xác minh.

```json
// request
{"email": " HS01@Example.com ", "password": "<mat-khau-cua-ban>", "display_name": "Học sinh 01"}
// 202, không đặt cookie
{"challenge":"<ma-yeu-cau>","email":"hs01@example.com","expires_in":300,"resend_after":60}
```

| Trường | Ràng buộc |
| --- | --- |
| `email` | Bắt buộc, đúng định dạng email, tối đa 255 ký tự. Được bỏ khoảng trắng hai đầu và chuyển về chữ thường. Duy nhất, không phân biệt hoa thường |
| `password` | Bắt buộc, 8–128 ký tự (trước review PR #17 là 6). Không bị cắt khoảng trắng |
| `display_name` | Tuỳ chọn, tối đa 100 ký tự. Chuỗi rỗng được lưu thành `null` |
| Trường khác (vd `role`) | Bị bỏ qua. Không cách nào tự đăng ký thành admin |

Tên miền dùng riêng như `.local`, `.test` bị coi là email sai định dạng (422).

### POST /auth/otp/verify

Nhận `{"challenge":"<ma-yeu-cau>","purpose":"registration","otp":"123456"}`. Mã đúng trả `201 UserOut` và đặt cookie phiên. Với `purpose: "google_email"`, mã đúng trả `200 UserOut`. Mỗi mã dùng một lần.

### POST /auth/otp/resend

Nhận `{"challenge":"<ma-yeu-cau>","purpose":"registration"}` hoặc mục đích `google_email`. Trả `202` với dữ liệu như bước đăng ký. Mã cũ hết hiệu lực. Chờ tối thiểu 60 giây giữa hai lượt gửi, tối đa 5 lượt mỗi email mỗi giờ cho mỗi mục đích.

### Đăng nhập Google

1. `POST /auth/google/start` nhận `{"challenge":"<S256-cua-verifier>"}` và trả `{"url":"<Google-OAuth-URL>"}`.
2. Google chuyển hướng về `GET /api/auth/google/callback` trên backend. Backend kiểm token rồi chuyển trình duyệt về `/login/google#ticket=...` ở frontend.
3. `POST /auth/google/exchange` nhận `{"ticket":"<ticket>","verifier":"<verifier>"}`. Trả `200 UserOut` và cookie hoặc trả `202` với yêu cầu OTP khi lần đầu dùng email có tên miền ngoài Google.

Xem [quy tắc nối tài khoản học sinh](../architecture/backend-auth.md#đăng-ký-và-đăng-nhập).

### POST /auth/login

Công khai. Đăng nhập bằng mật khẩu mở phiên khi thông tin đúng. Các phiên cũ vẫn dùng được. OTP áp dụng lúc đăng ký.

```json
// request
{"email": "hs01@example.com", "password": "<mat-khau-cua-ban>"}
// 200 + set-cookie như trên
{"user_id": 1, "email": "hs01@example.com", "role": "student", "status": "active", "display_name": null, "created_at": "2026-11-27T15:52:23.845134Z"}
```

`password` dài 1–128 ký tự: đăng nhập không áp luật 8 ký tự, nên tài khoản đã đặt mật khẩu 6–7 ký tự trước khi đổi luật vẫn đăng nhập được. Luật 8 ký tự chỉ áp cho mật khẩu mới (đăng ký, tạo admin). Email được chuẩn hoá như khi đăng ký.

### POST /auth/logout

**Idempotent, không cần phiên hợp lệ.** Luôn trả `204` không có body, kèm `set-cookie: examind_session=""; Max-Age=0; ...`. Nếu token (cookie hoặc Bearer) khớp một phiên chưa thu hồi, kể cả phiên đã hết hạn, thì phiên đó bị thu hồi ngay. Không có phiên, phiên đã hết hạn, đã thu hồi hay token không hợp lệ đều vẫn trả 204, nên frontend không phải xử lý lỗi khi đăng xuất. Sau đó, dùng lại token cũ sẽ nhận 401 `SESSION_REVOKED`.

### GET /auth/me

Cần phiên. Trả `UserOut` của người đang đăng nhập (200). Phản hồi có `Cache-Control: no-store`. Frontend gọi endpoint này khi tải trang để biết đã đăng nhập chưa và vai trò là gì.

### GET /admin/ping

Chỉ admin. Đây là endpoint mẫu chứng minh phân quyền.

```json
// 200
{"status": "ok", "user_id": 2, "role": "admin"}
```

## Lỗi và trường hợp biên

Lỗi nghiệp vụ trả body `{"detail": "<thông báo tiếng Việt>", "code": "<MÃ>"}`. Frontend phân nhánh theo `code`, không theo `detail`. Lỗi 422 do kiểm schema giữ định dạng mặc định của FastAPI: `detail` là một mảng lỗi theo trường và không có `code`.

| HTTP | `code` | Khi nào | Frontend nên làm gì |
| --- | --- | --- | --- |
| 422 | (không có) | Email sai định dạng; mật khẩu mới < 8 hoặc > 128 ký tự; thiếu trường | Hiện lỗi ở trường tương ứng |
| 409 | `EMAIL_TAKEN` | Đăng ký với email đã có (không phân biệt hoa thường) | Gợi ý đăng nhập. Việc này cố ý cho biết email đã tồn tại |
| 401 | `INVALID_CREDENTIALS` | Đăng nhập sai email **hoặc** sai mật khẩu. Hai trường hợp có cùng thông báo và thời gian xử lý tương đương | "Email hoặc mật khẩu không đúng" |
| 403 | `ACCOUNT_DISABLED` | Đăng nhập đúng mật khẩu nhưng tài khoản bị khoá, **hoặc** gọi API bằng phiên của tài khoản vừa bị khoá | Báo tài khoản bị khoá, không thử lại |
| 401 | `SESSION_MISSING` | Không có cookie và không có Bearer | Chuyển tới trang đăng nhập |
| 401 | `SESSION_INVALID` | Token không khớp phiên nào | Chuyển tới trang đăng nhập |
| 401 | `SESSION_EXPIRED` | Phiên quá `expires_at` | Báo hết phiên, chuyển tới trang đăng nhập |
| 401 | `SESSION_REVOKED` | Phiên đã đăng xuất | Chuyển tới trang đăng nhập |
| 403 | `FORBIDDEN_ROLE` | Đăng nhập rồi nhưng sai vai trò (vd student gọi API admin) | Báo không có quyền, không chuyển tới trang đăng nhập |
| 400 | `OTP_INVALID`, `OTP_EXPIRED`, `INVALID_CHALLENGE` | Sai mã, hết hạn hoặc yêu cầu đã kết thúc | Thử lại hoặc gửi mã mới theo thông báo |
| 429 | `TOO_MANY_ATTEMPTS`, `OTP_RESEND_LIMIT` | Đã thử sai 5 lần hoặc vượt giới hạn gửi | Chờ và gửi mã mới |
| 400 | `GOOGLE_INVALID` | Ticket hết hạn, đã dùng hoặc verifier không khớp | Bắt đầu lại đăng nhập Google |
| 409 | `GOOGLE_ACCOUNT_CONFLICT` | Email thuộc admin hoặc đã nối Google khác | Dùng phương thức đăng nhập của tài khoản hiện có |
| 503 | `EMAIL_UNAVAILABLE`, `GOOGLE_UNAVAILABLE` | Cấu hình chưa sẵn sàng hoặc gửi thư thất bại | Thử lại sau |

- Mọi phản hồi 401 có header `WWW-Authenticate: Bearer`.
- Các phản hồi `SESSION_INVALID`, `SESSION_EXPIRED`, `SESSION_REVOKED`, `ACCOUNT_DISABLED` kèm lệnh xoá cookie.
- Chưa giới hạn số lần thử đăng nhập hay đăng ký (xem mục "Chưa làm" trong [backend-auth.md](../architecture/backend-auth.md#chưa-làm)).
- Ví dụ 422 khi mật khẩu quá ngắn:

  ```json
  {"detail": [{"type": "string_too_short", "loc": ["body", "password"], "msg": "String should have at least 8 characters"}]}
  ```

- Không phải mọi 401 đều là mất phiên. API quản lý admin trả 401 `REAUTH_FAILED` khi mật khẩu xác nhận sai, lúc đó phiên vẫn còn ([admin-accounts-api.md](admin-accounts-api.md#lỗi-và-trường-hợp-biên)). Frontend phân nhánh theo `code`: chỉ `SESSION_MISSING`, `SESSION_INVALID`, `SESSION_EXPIRED`, `SESSION_REVOKED` mới chuyển tới trang đăng nhập.

## Áp dụng quyền cho #3, #4, #5, #11

Dùng các dependency trong `app/api/deps.py`. Không tự đọc cookie hay header trong router.

| Dependency | Dùng khi | Kết quả trong route |
| --- | --- | --- |
| `CurrentUserDep` | Mọi người đã đăng nhập | `CurrentUser` có `.user_id`, `.role`, `.user`, `.session_id` |
| `StudentDep` | Chỉ học sinh (#4 chat tạo đề, đề nháp) | Như trên; admin nhận 403 `FORBIDDEN_ROLE` |
| `AdminDep` | Chỉ admin (#3 nhập PDF, #11 ngân hàng câu, #5 sửa mẫu đề) | Như trên; student nhận 403 `FORBIDDEN_ROLE` |
| `Depends(require_role("student", "admin"))` | Nhiều vai trò cùng được | Như trên |

Ví dụ cho cả router admin (#3, #11), theo mẫu `app/api/v1/admin.py`:

```python
from fastapi import APIRouter, Depends
from app.api.deps import AdminDep, require_role

router = APIRouter(prefix="/admin/questions", tags=["admin"], dependencies=[Depends(require_role("admin"))])

@router.get("")
async def list_questions(current: AdminDep, usecase: QuestionUseCaseDep): ...
```

Ví dụ cho tài nguyên của học sinh (#4): kiểm chủ sở hữu trong usecase và trả 404 nếu không phải của mình.

```python
@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: int, current: StudentDep, usecase: DraftUseCaseDep):
    draft = await usecase.get_for_owner(draft_id, owner_id=current.user_id)  # None nếu không có hoặc không phải của mình
    if draft is None:
        raise HTTPException(404, "Không có đề nháp này")
    return draft
```

Với SSE, dùng cùng dependency. `EventSource` tự gửi cookie khi cùng origin; không truyền token qua query string. Chi tiết ở [backend-auth.md](../architecture/backend-auth.md#áp-dụng-cho-sse-4).

Trong test, tạo người dùng rồi đăng nhập qua API như `tests/test_auth.py`. Admin tạo bằng `AuthUseCase.create_user(..., "admin")` (hàm `make_admin` trong cùng file).

## Hướng dẫn mock cho frontend

Hai tài khoản dưới đây là **giá trị mock, chỉ dùng phía frontend ở chế độ mock** (`NEXT_PUBLIC_MOCK_MODE=true`). Backend thật không có sẵn tài khoản hay mật khẩu nào: không dùng các giá trị này cho DB local, EC2 hay bất kỳ môi trường thật nào. Email dùng tên miền `example.com` dành cho tài liệu.

| Vai trò | Email | Mật khẩu mock (chỉ chế độ mock) |
| --- | --- | --- |
| student | `hs01@example.com` | `mock-hs01` |
| admin | `admin@example.com` | `mock-admin` |

Mock theo bảng sau (đường dẫn tương đối, cùng origin):

| Request | Mock trả |
| --- | --- |
| `POST /api/v1/auth/login` đúng tài khoản student | 200, body bên dưới |
| `POST /api/v1/auth/login` đúng tài khoản admin | 200, body bên dưới |
| `POST /api/v1/auth/login` sai | 401 `{"detail": "Email hoặc mật khẩu không đúng", "code": "INVALID_CREDENTIALS"}` |
| `POST /api/v1/auth/register` email mới | 202, dùng mã mock `123456` để tạo tài khoản học sinh |
| `POST /api/v1/auth/register` email `hs01@example.com` | 409 `{"detail": "Email này đã được đăng ký", "code": "EMAIL_TAKEN"}` |
| `GET /api/v1/auth/me` khi đã đăng nhập | 200, `UserOut` của người đã đăng nhập |
| `GET /api/v1/auth/me` khi chưa đăng nhập | 401 `{"detail": "Chưa đăng nhập", "code": "SESSION_MISSING"}` |
| `POST /api/v1/auth/logout` | 204, xoá trạng thái đăng nhập của mock |
| `GET /api/v1/admin/ping` với student | 403 `{"detail": "Tài khoản không có quyền dùng chức năng này", "code": "FORBIDDEN_ROLE"}` |

```json
// student
{"user_id": 1, "email": "hs01@example.com", "role": "student", "status": "active", "display_name": "Học sinh 01", "created_at": "2026-11-27T15:52:23.845134Z"}
// admin
{"user_id": 2, "email": "admin@example.com", "role": "admin", "status": "active", "display_name": "Quản trị", "created_at": "2026-11-27T15:52:41.085593Z"}
```

Gợi ý cho Redux: chỉ lưu `UserOut` trong store, không lưu token. Khi nhận 401 với `code` bắt đầu bằng `SESSION_` thì xoá user khỏi store và chuyển tới trang đăng nhập; 401 `REAUTH_FAILED` chỉ là sai mật khẩu xác nhận, giữ phiên. Khi nhận 403 `FORBIDDEN_ROLE` thì giữ phiên và báo không có quyền. Mock cho trang quản lý admin: [admin-accounts-api.md](admin-accounts-api.md#hướng-dẫn-mock-cho-frontend).

Muốn có tài khoản tương tự trên DB local thật: đặt `ADMIN_EMAIL` và `ADMIN_PASSWORD` (mật khẩu của riêng bạn, không dùng giá trị mock) trong `.env` để `docker compose up` tự tạo admin, rồi đăng ký một học sinh qua API ([run-local-stack.md](../operations/run-local-stack.md)).

## Luồng kiểm thử

Đã chạy ngày 2026-11-27 trên Windows 11, backend chạy trực tiếp, PostgreSQL 16 trong Docker. `-c`/`-b` dùng cookie jar như trình duyệt. Trong kết quả, token được thay bằng `<token>`.

Đặt mật khẩu vào biến môi trường của phiên shell trước khi chạy (không ghi vào file, không commit). PowerShell: `$env:HS01_PASSWORD='...'`.

```bash
B=http://localhost:8000/api/v1
export HS01_PASSWORD='<mat-khau-cua-ban>' ADMIN_PASSWORD='<mat-khau-admin>'
curl -s -i -c jar.txt -b jar.txt -X POST $B/auth/register -H "content-type: application/json" \
  -d "{\"email\":\" HS01@Example.com \",\"password\":\"$HS01_PASSWORD\",\"role\":\"admin\"}"
# 202. Thay email ví dụ bằng email bạn kiểm soát để nhận mã.
curl -s -i -c jar.txt -b jar.txt -X POST "$B/auth/otp/verify" -H "content-type: application/json" \
  -d '{"challenge":"<ma-yeu-cau>","purpose":"registration","otp":"<ma-trong-email>"}'
# 201, UserOut và cookie examind_session.
curl -s -i -c jar.txt -b jar.txt $B/auth/me                # 200 UserOut
curl -s -i -c jar.txt -b jar.txt -X POST $B/auth/logout    # 204, set-cookie examind_session=""; Max-Age=0
curl -s -i -c jar.txt -b jar.txt $B/auth/me                # 401 {"detail":"Chưa đăng nhập","code":"SESSION_MISSING"}
curl -s -i -c jar.txt -b jar.txt -X POST $B/auth/login -H "content-type: application/json" \
  -d "{\"email\":\"hs01@example.com\",\"password\":\"$HS01_PASSWORD\"}"  # 200, đặt cookie mới
curl -s -i -c jar.txt -b jar.txt $B/admin/ping             # 403 FORBIDDEN_ROLE

# Tạo admin (trong backend/). Lần chạy thứ hai báo đã có và thoát mã 1.
python -m app.cli.create_admin --email admin@example.com --name "Quản trị"   # đọc $ADMIN_PASSWORD
curl -s -i -c admin.txt -b admin.txt -X POST $B/auth/login -H "content-type: application/json" \
  -d "{\"email\":\"admin@example.com\",\"password\":\"$ADMIN_PASSWORD\"}"  # 200, role admin
curl -s -i -c admin.txt -b admin.txt $B/admin/ping         # 200 {"status":"ok","user_id":2,"role":"admin"}
```

Các ca lỗi đã kiểm cùng ngày:

| Thao tác | Kết quả |
| --- | --- |
| Đăng nhập sai mật khẩu | 401 `INVALID_CREDENTIALS` |
| Bearer của phiên đã đăng xuất | 401 `SESSION_REVOKED` |
| Đặt `users.status='disabled'` bằng SQL, rồi gọi `/auth/me` bằng phiên đang mở | 403 `ACCOUNT_DISABLED` |
| Đăng nhập tài khoản đã khoá, đúng mật khẩu | 403 `ACCOUNT_DISABLED` |
| Đặt `sessions.expires_at` về quá khứ, rồi gọi `/admin/ping` | 401 `SESSION_EXPIRED`, kèm xoá cookie |

Chạy `python -m pytest -q` trong `backend/`. Test OTP và Google thay nhà cung cấp bằng dịch vụ giả lập.

## Tài liệu liên quan

- [Xác thực và phân quyền backend](../architecture/backend-auth.md)
- [API mẫu](sample-api.md) (định dạng lỗi gốc)
- Mã: `backend/app/api/v1/auth.py`, `backend/app/api/v1/admin.py`, `backend/app/api/deps.py`
