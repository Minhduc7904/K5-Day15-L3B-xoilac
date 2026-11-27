# Các lớp backend

Dành cho người viết tính năng mới trong `backend/app/`. Backend theo Clean Architecture, tách bốn lớp và một chiều phụ thuộc.

## Bối cảnh và ràng buộc

- Issue #1 yêu cầu tách `api`, `usecase`, `service`, `repositories`, dùng ORM cho PostgreSQL và API tương thích S3 cho MinIO.
- Mọi lớp ở dưới chỉ được gọi bởi lớp ở trên. Lớp trên không biết chi tiết cài đặt của lớp dưới ngoài giao diện được ghép ở `deps.py`.

## Thành phần và trách nhiệm

```
api  →  usecase  →  service / repositories  →  models, PostgreSQL, MinIO
```

| Lớp | Thư mục | Làm gì | Không làm gì |
| --- | --- | --- | --- |
| API | `app/api/` | Nhận request, kiểm đầu vào bằng schema, gọi usecase, đổi lỗi thành mã HTTP | Không chứa luật nghiệp vụ, không gọi repository hay service trực tiếp |
| Usecase | `app/usecase/` | Một luồng nghiệp vụ trọn vẹn, ghép repository và service | Không biết HTTP, không viết SQL |
| Service | `app/service/` | Giao tiếp hệ thống ngoài (MinIO; sau này OCR, model) | Không biết luật nghiệp vụ |
| Repositories | `app/repositories/` | Đọc ghi DB qua ORM | Không chứa luật nghiệp vụ |

Thư mục hỗ trợ:

- `app/models/`: model ORM. `Base.metadata` là nguồn cho Alembic.
- `app/schemas/`: Pydantic cho request và response.
- `app/core/`: cấu hình (`config.py`, đọc `backend/.env`) và kết nối DB (`database.py`).
- `app/api/deps.py`: nơi duy nhất ghép các lớp bằng dependency injection của FastAPI. Test thay thế phần phụ thuộc ở đây.
- `alembic/`: migration.

## Luồng dữ liệu và tích hợp

Ví dụ `POST /api/v1/sample-items`: `api/v1/sample_items.py` nhận body đã kiểm bằng `SampleItemCreate` → `SampleItemUseCase.create` chuẩn hoá tên → `SampleItemRepository.add` ghi bằng session async → trả `SampleItemOut`.

Ví dụ `POST /api/v1/sample-files`: router đọc tệp (tối đa 5 MB) → `SampleFileUseCase.upload` sinh khoá `samples/<uuid>` → `StorageService.put` gọi MinIO. `boto3` là đồng bộ nên được gọi trong threadpool.

## Quyết định và cách kiểm chứng

Thêm tính năng mới:

1. Thêm model trong `app/models/` và import vào `app/models/__init__.py`.
2. Sinh migration bằng `alembic revision -m "..."` rồi sửa; đặt tên rõ nghĩa.
3. Thêm repository, service nếu cần hệ thống ngoài, rồi usecase.
4. Thêm router trong `app/api/v1/`, đăng ký ở `router.py`, ghép phụ thuộc ở `deps.py`.
5. Viết test trong `backend/tests/` (dùng `FakeStorage` và SQLite trong `conftest.py`).
6. Ghi tài liệu API vào `docs/api/<tính-năng>-api.md` và thêm dòng vào [mục lục](../README.md).

| Issue | Gợi ý nơi đặt |
| --- | --- |
| #3 nhập PDF | `usecase/` + `service/` (OCR, tách câu, embedding), router `api/v1/admin_import.py` |
| #4 chat tạo đề | router SSE `api/v1/exam_chat.py`; gọi `codebase/agent.py` qua một service riêng |
| #5 mẫu cấu trúc đề | `models/exam_template.py`, repository và usecase tương ứng |

Endpoint cần đăng nhập hoặc cần vai trò dùng `CurrentUserDep`, `StudentDep`, `AdminDep` hoặc `require_role(...)` trong `deps.py` (issue #8). Xem [backend-auth.md](backend-auth.md) và [auth-api.md](../api/auth-api.md#áp-dụng-quyền-cho-3-4-5-11).

Kiểm chứng: `cd backend && pytest -q` (không cần Docker).

## Tài liệu liên quan

- [Tổng quan hệ thống](system-overview.md)
- [Xác thực và phân quyền backend](backend-auth.md)
- [API mẫu](../api/sample-api.md)
- [Chạy bộ khung local](../operations/run-local-stack.md)
