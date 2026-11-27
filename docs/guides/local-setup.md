# Chạy local

**Mục đích:** dựng bộ khung trên máy và kiểm tiêu chí nghiệm thu · **Người phụ trách:** Nguyễn Minh Đức · **Issue:** #1 · **Cập nhật:** 2026-11-27

## Yêu cầu

- Python 3.12, Docker Desktop (có `docker compose`).
- Node 22 và npm 10 cho frontend *(frontend chưa có trong nhánh này; mục tương ứng sẽ thêm sau)*.

## 1. Hạ tầng: PostgreSQL và MinIO

Từ thư mục gốc repo:

```
docker compose up -d
docker compose ps -a
```

Mong đợi: `postgres` và `minio` ở trạng thái healthy; `db-init` và `minio-init` **Exited (0)**. Hai container này chạy một lần rồi thoát, chạy lại không tạo trùng.

- MinIO console: http://localhost:9001 (mặc định `minioadmin` / `minioadmin`, chỉ cho máy dev).
- Đổi cổng hoặc mật khẩu bằng biến môi trường (xem đầu `docker-compose.yml`).

Lần đầu `db-init` build image backend, cần mạng để cài thư viện Python. Mạng yếu thì chạy lại `docker compose build db-init`.

## 2. Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Tài liệu API tự sinh: http://localhost:8000/docs

## 3. Kiểm tiêu chí nghiệm thu (backend)

```
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/sample-items -H "content-type: application/json" -d "{\"name\":\"de mau\"}"
curl http://localhost:8000/api/v1/sample-items
curl -F "file=@ten-tep.txt;type=text/plain" http://localhost:8000/api/v1/sample-files
curl http://localhost:8000/api/v1/sample-files/<key trả về ở lệnh trên>
```

- `health` trả `{"status":"ok","database":true,"storage":true}`.
- Bản ghi tạo ra đọc lại được qua `GET /sample-items` (ORM + PostgreSQL).
- Tệp tải lên tải lại đúng nội dung (MinIO).

Chạy test (không cần Docker, dùng SQLite và MinIO giả):

```
cd backend
pytest
```

## Dọn dẹp

```
docker compose down        # giữ dữ liệu
docker compose down -v     # xoá cả dữ liệu PostgreSQL và MinIO
```

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `health` báo `storage: false` | `docker compose ps`: `minio` phải healthy; kiểm `S3_*` trong `backend/.env` khớp compose |
| `health` báo `database: false` | Kiểm `DATABASE_URL`, cổng 5432 có bị chương trình khác chiếm |
| Docker không kéo được image MinIO | `minio/minio` đã bị gỡ khỏi Docker Hub; compose dùng `bitnamilegacy/minio` |
