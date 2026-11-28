# Chạy bộ khung local

Dành cho thành viên nhóm cần dựng PostgreSQL, MinIO và backend trên máy cá nhân, rồi kiểm các tiêu chí nghiệm thu của issue #1. Frontend chưa có; phần chạy frontend sẽ được thêm khi hoàn thiện.

## Điều kiện trước khi chạy

- Python 3.12, Docker Desktop (có `docker compose`).
- Mạng để kéo image và cài thư viện Python lần đầu.
- Các lệnh `docker compose` chạy ở thư mục gốc repo; các lệnh Python chạy trong `backend/`.

## Thông tin môi trường

| Mục | Giá trị mặc định (chỉ cho máy dev) |
| --- | --- |
| PostgreSQL | `localhost:5432`, user/mật khẩu/db `examind` |
| MinIO API | `http://localhost:9000`, `minioadmin` / `minioadmin` |
| MinIO console | `http://localhost:9001` |
| Bucket | `examind` |
| Backend | `http://localhost:8000` |

Đổi cổng hoặc mật khẩu bằng biến môi trường (xem đầu `docker-compose.yml`). Backend đọc `backend/.env`, mẫu ở `backend/.env.example`. Giá trị trong `.env` phải khớp compose.

Biến của phiên đăng nhập (issue #8): `COOKIE_NAME` (mặc định `examind_session`), `COOKIE_SECURE` (local để `false` vì chạy HTTP), `SESSION_TTL_HOURS` (mặc định `168`). Đặt `CORS_ORIGINS=http://localhost:3000` để frontend nối Socket.IO trực tiếp, kể cả khi REST đi qua rewrite. Trên prod, các biến này và `ADMIN_*` nằm trong `/opt/examind/prod.env`, xem [deploy-backend-ci-cd.md](deploy-backend-ci-cd.md#biến-trong-prodenv).

## Các bước thực hiện

1. Đặt admin mặc định. Compose đọc file `.env` ở **thư mục gốc** repo (cùng file với `MODEL_PROVIDER`, chép từ `.env.example`). Thêm hoặc sửa ba dòng:

   ```bash
   ADMIN_EMAIL=admin@example.com
   ADMIN_NAME=Quản trị
   ADMIN_PASSWORD=<tự đặt, 8–128 ký tự; prod cần ≥ 12>
   ```

   Không commit `.env`. Trong mật khẩu tránh ký tự `$`, vì compose coi `$` là chỗ thay biến (nếu cần thì viết `$$`). Bỏ trống `ADMIN_EMAIL` hoặc `ADMIN_PASSWORD` thì không có admin mặc định.

2. Dựng hạ tầng:

   ```bash
   docker compose up -d
   docker compose ps -a
   docker compose logs db-init
   ```

   Mong đợi: `postgres` và `minio` healthy; `db-init` và `minio-init` ở trạng thái `Exited (0)`. Hai container này chạy một lần rồi thoát, chạy lại không tạo trùng. Lần đầu `db-init` build image backend nên mất vài phút. Log `db-init` có dòng `Đã tạo admin mặc định user_id=1 email=admin@example.com`; các lần sau là `Admin mặc định đã có, không thay đổi`. `db-init` ở trạng thái `Exited (2)` nghĩa là cấu hình admin sai, xem bảng xử lý lỗi.

3. Cài backend:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements-dev.txt
   copy .env.example .env          # macOS/Linux: cp .env.example .env
   ```

   `backend/.env` cũng có `ADMIN_*` (để trống mật khẩu) cho trường hợp chạy `python -m app.cli.ensure_admin` trực tiếp trên máy, vd khi dùng PostgreSQL ngoài compose. Lệnh này cho cùng kết quả như trong `db-init`.

4. Chạy backend:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Thêm admin khác: đăng nhập bằng admin mặc định rồi gọi `POST /api/v1/admin/accounts` kèm mật khẩu của chính mình ([admin-accounts-api.md](../api/admin-accounts-api.md)). Đổi `ADMIN_PASSWORD` sau lần tạo đầu **không** đổi mật khẩu của admin đã có.

6. Cứu hộ khi mọi admin đều bị khoá hoặc quên mật khẩu: tạo một admin mới bằng tay (trong `backend/`), đăng nhập bằng admin đó rồi mở khoá các admin khác qua API.

   ```bash
   python -m app.cli.create_admin --email rescue@example.com --name "Cứu hộ"
   ```

   Lệnh hỏi mật khẩu hai lần (8–128 ký tự) và không nhận mật khẩu qua tham số. Khi chạy không tương tác (script, `docker exec` không có `-t`), đặt biến `ADMIN_PASSWORD` cho riêng lệnh đó, vd `ADMIN_PASSWORD='...' python -m app.cli.create_admin --email ...` (PowerShell: `$env:ADMIN_PASSWORD='...'`, chạy xong thì `Remove-Item Env:ADMIN_PASSWORD`). Trên Windows, `getpass` đọc thẳng từ console, nên chuyển hướng stdin sẽ làm lệnh treo; trường hợp đó dùng `ADMIN_PASSWORD`.

   | Mã thoát | Ý nghĩa |
   | --- | --- |
   | 0 | Đã tạo admin |
   | 1 | Email đã có tài khoản; không tạo trùng, không đổi vai trò hay mật khẩu |
   | 2 | Email sai định dạng (tên miền `.local`, `.test` cũng bị từ chối), mật khẩu sai độ dài hoặc không đọc được mật khẩu |

   Trên VPS, chạy trong container backend: `docker compose ... exec -e ADMIN_PASSWORD backend python -m app.cli.create_admin --email <email>`, sau khi đã `export ADMIN_PASSWORD` trong phiên SSH.

Nếu có gói dữ liệu nền ở `data/private/seed` (biến `SEED_DIR`), hai container init nạp thêm câu hỏi, đề và ảnh đúng một lần; không có thì chỉ tạo bảng. Cách dựng gói: [seed-base-data.md](seed-base-data.md). Cổng PostgreSQL và MinIO chỉ mở trên `127.0.0.1`.

Quay lui: `docker compose down` giữ dữ liệu; `docker compose down -v` xoá cả dữ liệu PostgreSQL và MinIO.

## Kiểm tra kết quả

```bash
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/sample-items -H "content-type: application/json" -d "{\"name\":\"de mau\"}"
curl http://localhost:8000/api/v1/sample-items
curl -F "file=@ten-tep.txt;type=text/plain" http://localhost:8000/api/v1/sample-files
curl http://localhost:8000/api/v1/sample-files/<key trả về ở lệnh trên>
```

- `health` trả `{"status":"ok","database":true,"storage":true}`.
- Bản ghi tạo ra đọc lại được qua `GET /sample-items` (ORM và PostgreSQL).
- Tệp tải lên tải lại đúng nội dung (MinIO).
- Đăng ký, đăng nhập và phân quyền: chạy luồng curl ở [auth-api.md](../api/auth-api.md#luồng-kiểm-thử).
- Admin mặc định và quản lý admin: luồng curl ở [admin-accounts-api.md](../api/admin-accounts-api.md#luồng-kiểm-thử).

Test tự động không cần Docker (dùng SQLite và MinIO giả): `cd backend && pytest`.

Giới hạn xác minh: các bước trên đã chạy trên Windows 11 với Docker 29.3 ngày 2026-11-27; phần admin mặc định (bước 1–2, 5–6) chạy với Docker 28.4 ngày 2026-11-28. Chưa thử macOS/Linux.

## Chạy worker học sinh

Sau khi PostgreSQL đã chạy migration, mở terminal riêng trong `backend/` và kích hoạt venv như khi chạy API.

```bash
python -m app.worker
python -m app.worker --once --job daily-credit
python -m app.worker --once --job study-reminders
python -m app.worker --once --job exam-expiry
```

`--once` chạy một lượt đến hạn rồi thoát. Khi chạy liên tục, `exam-expiry` quét lượt làm có thời lượng đã tới hạn mỗi 2 giây. Chạy migration `0015_exam_attempts` trước khi bật luồng làm bài online. Khi kiểm thử giao dịch đồng thời trên PostgreSQL, trỏ `EXAM_ATTEMPT_TEST_DATABASE_URL` vào cơ sở dữ liệu thử riêng đã chạy `python -m alembic upgrade head`, rồi chạy `python -m pytest -q tests/test_exam_attempts.py` trong `backend/`. `daily-credit` xử lý theo ngày Việt Nam. `study-reminders` chỉ chạy khi `EMAIL_PROVIDER=gmail`. Khi thử gửi thật, dùng tài khoản và hộp thư bạn kiểm soát, bật nhắc và chọn giờ đã đến trong ngày hiện tại. Nếu chạy UI thật, giữ `NEXT_PUBLIC_MOCK_MODE=false` và đặt `NEXT_PUBLIC_SOCKET_URL=http://localhost:8000`.

## Xử lý lỗi

| Triệu chứng | Nguyên nhân và cách xử lý |
| --- | --- |
| `health` báo `storage: false` | `docker compose ps`: `minio` phải healthy; kiểm `S3_*` trong `backend/.env` khớp compose |
| `health` báo `database: false` | Kiểm `DATABASE_URL`; cổng 5432 có bị chương trình khác chiếm không |
| `docker compose` không kéo được MinIO | `minio/minio` đã bị gỡ khỏi Docker Hub; compose dùng `bitnamilegacy/minio` |
| `db-init` lỗi khi cài thư viện (timeout) | Mạng yếu; chạy lại `docker compose build db-init` rồi `docker compose up -d` |
| `db-init` `Exited (0)` nhưng log có `CẢNH BÁO: ... không phải admin` và không có admin | `ADMIN_EMAIL` đang là tài khoản student. Lệnh không nâng quyền, không đổi gì; đổi `ADMIN_EMAIL` sang email khác rồi `docker compose up -d` |
| `db-init` `Exited (2)`, log `Lỗi admin mặc định: ...` | Email sai định dạng (`.local`, `.test` cũng bị từ chối) hoặc mật khẩu sai độ dài (prod: ≥ 12 ký tự) |
| Không đăng nhập được admin mặc định sau khi đổi `ADMIN_PASSWORD` | `ensure_admin` không ghi đè mật khẩu của admin đã có. Dùng mật khẩu cũ, hoặc trên máy dev `docker compose down -v` để dựng lại từ đầu (mất dữ liệu) |

## Tài liệu liên quan

- [Tổng quan hệ thống](../architecture/system-overview.md)
- [API mẫu](../api/sample-api.md)
- [Runbook EC2](deploy-ec2.md)
