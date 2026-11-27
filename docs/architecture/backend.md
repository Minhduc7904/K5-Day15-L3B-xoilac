# Kiến trúc backend

**Mục đích:** quy ước các lớp và chiều phụ thuộc của backend · **Người phụ trách:** Nguyễn Minh Đức · **Issue:** #1 · **Cập nhật:** 2026-11-27

Backend theo Clean Architecture, tách bốn lớp. Mã nằm trong `backend/app/`.

```
api  →  usecase  →  service / repositories  →  models, PostgreSQL, MinIO
```

| Lớp | Thư mục | Làm gì | Không làm gì |
|---|---|---|---|
| API | `app/api/` | Nhận request, kiểm đầu vào bằng schema, gọi usecase, đổi lỗi thành mã HTTP | Không chứa luật nghiệp vụ, không gọi repository hay service trực tiếp |
| Usecase | `app/usecase/` | Một luồng nghiệp vụ trọn vẹn, ghép repository và service | Không biết HTTP, không viết SQL |
| Service | `app/service/` | Giao tiếp hệ thống ngoài (MinIO, sau này là OCR, model) | Không biết luật nghiệp vụ |
| Repositories | `app/repositories/` | Đọc ghi DB qua ORM | Không chứa luật nghiệp vụ |

Thư mục hỗ trợ:

- `app/models/`: model ORM, `Base.metadata` là nguồn cho Alembic.
- `app/schemas/`: Pydantic cho request và response.
- `app/core/`: cấu hình (`config.py`, đọc `backend/.env`) và kết nối DB (`database.py`).
- `app/api/deps.py`: nơi duy nhất ghép các lớp bằng dependency injection của FastAPI. Test thay thế phần phụ thuộc ở đây.
- `alembic/`: migration. Sinh bản mới bằng `alembic revision -m "..."`.

## Điểm mẫu có sẵn

| Endpoint (`/api/v1`) | Chứng minh |
|---|---|
| `GET /health` | Kết nối được DB và MinIO |
| `POST/GET /sample-items` | Ghi và đọc một bản ghi qua ORM (bảng `sample_items`, migration `0001`) |
| `POST /sample-files`, `GET /sample-files/{key}` | Ghi và đọc một tệp qua MinIO (khoá bắt đầu bằng `samples/`, tối đa 5 MB) |

Đây chỉ là mẫu để xoá hoặc thay khi có tính năng thật.

## Thêm tính năng mới

1. Thêm model trong `app/models/` và import vào `app/models/__init__.py`.
2. Sinh migration, đặt tên rõ nghĩa. Mỗi issue một nhóm migration.
3. Thêm repository, service nếu cần hệ thống ngoài, rồi usecase.
4. Thêm router trong `app/api/v1/`, đăng ký ở `router.py`, ghép phụ thuộc ở `deps.py`.
5. Viết test trong `backend/tests/` (dùng `FakeStorage` và SQLite trong `conftest.py`).
6. Ghi tài liệu API vào `docs/api/` và thêm dòng vào `docs/README.md`.

| Issue | Gợi ý nơi đặt |
|---|---|
| #3 nhập PDF | `usecase/` + `service/` (OCR, tách câu, embedding), router `api/v1/admin_import.py` |
| #4 chat tạo đề | router SSE `api/v1/exam_chat.py`; gọi `codebase/agent.py` qua một service riêng |
| #5 mẫu cấu trúc đề | `models/exam_template.py`, repository và usecase tương ứng |

## Giới hạn hiện tại

- `boto3` là đồng bộ, được gọi trong threadpool (`StorageService`). Đủ cho khung; xét lại nếu upload lớn.
- Chưa có xác thực và phân quyền; thêm cùng issue đầu tiên cần quyền admin.
