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

## Các bước thực hiện

1. Dựng hạ tầng:

   ```bash
   docker compose up -d
   docker compose ps -a
   ```

   Mong đợi: `postgres` và `minio` healthy; `db-init` và `minio-init` ở trạng thái `Exited (0)`. Hai container này chạy một lần rồi thoát, chạy lại không tạo trùng. Lần đầu `db-init` build image backend nên mất vài phút.

2. Cài backend:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
   pip install -r requirements-dev.txt
   copy .env.example .env          # macOS/Linux: cp .env.example .env
   ```

3. Chạy backend:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

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

Test tự động không cần Docker (dùng SQLite và MinIO giả): `cd backend && pytest`.

Giới hạn xác minh: các bước trên đã chạy trên Windows 11 với Docker 29.3 ngày 2026-11-27; chưa thử macOS/Linux.

## Xử lý lỗi

| Triệu chứng | Nguyên nhân và cách xử lý |
| --- | --- |
| `health` báo `storage: false` | `docker compose ps`: `minio` phải healthy; kiểm `S3_*` trong `backend/.env` khớp compose |
| `health` báo `database: false` | Kiểm `DATABASE_URL`; cổng 5432 có bị chương trình khác chiếm không |
| `docker compose` không kéo được MinIO | `minio/minio` đã bị gỡ khỏi Docker Hub; compose dùng `bitnamilegacy/minio` |
| `db-init` lỗi khi cài thư viện (timeout) | Mạng yếu; chạy lại `docker compose build db-init` rồi `docker compose up -d` |

## Tài liệu liên quan

- [Tổng quan hệ thống](../architecture/system-overview.md)
- [API mẫu](../api/sample-api.md)
- [Runbook EC2](deploy-ec2.md)
