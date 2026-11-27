# API mẫu của bộ khung

Các endpoint mẫu chứng minh backend nối được PostgreSQL và MinIO. Dành cho frontend khi gọi thử và cho người viết API mới tham khảo định dạng. Đây không phải API nghiệp vụ; xoá hoặc thay khi có tính năng thật.

## Điều kiện gọi

- Base URL local: `http://localhost:8000/api/v1`. Tài liệu tự sinh: `http://localhost:8000/docs`.
- Các endpoint mẫu không cần đăng nhập. Đăng nhập và phân quyền: [auth-api.md](auth-api.md). Dữ liệu gửi dạng JSON, riêng upload dùng `multipart/form-data`.
- CORS chỉ bật khi `CORS_ORIGINS` có giá trị (mặc định rỗng từ issue #8; `backend/.env.example` đặt `http://localhost:3000` cho dev).
- Base URL trên VPS: `https://examind.duckdns.org/api/v1` (cổng 80 HTTP vẫn mở, xem [deploy-backend-ci-cd.md](../operations/deploy-backend-ci-cd.md)). Tài liệu tự sinh: `https://examind.duckdns.org/docs`.

## Endpoint và hợp đồng

### GET /health

Báo trạng thái kết nối. Không cần tham số.

```json
{"status": "ok", "database": true, "storage": true}
```

`status` là `degraded` khi một trong hai là `false`; mã HTTP vẫn là 200.

### GET /health/live

Kiểm tra process còn sống, không chạm PostgreSQL hay MinIO nên luôn nhanh. Dùng để phân biệt "app chết" với "phụ thuộc lỗi" (khi đó `/health` báo `degraded`). Không cần tham số.

```json
{"status": "ok", "version": "0.1.0"}
```

### POST /sample-items

Ghi một bản ghi qua ORM.

```json
// request
{"name": "de mau"}
// response 201
{"id": 1, "name": "de mau", "created_at": "2026-11-27T12:13:20.362782Z"}
```

`name` dài 1–255 ký tự; khoảng trắng đầu cuối được cắt.

### GET /sample-items

Trả tối đa 50 bản ghi, mới nhất trước: mảng các đối tượng như trên.

### GET /sample-items/{id}

Trả một bản ghi. Mã 404 nếu không có.

### POST /sample-files

Tải một tệp lên MinIO. Trường form `file`, tối đa 5 MB.

```json
// response 201
{"key": "samples/2e362f1885ba4252a4c07bd40ebfe1fa", "size": 14, "content_type": "text/plain"}
```

### GET /sample-files/{key}

Tải lại tệp, phản hồi là nội dung tệp với đúng `Content-Type`. Chỉ khoá bắt đầu bằng `samples/` được phục vụ.

## Lỗi và trường hợp biên

| Mã | Khi nào |
| --- | --- |
| 404 | Không có bản ghi; khoá tệp không tồn tại hoặc không bắt đầu bằng `samples/` |
| 413 | Tệp lớn hơn 5 MB |
| 422 | `name` rỗng hoặc dài quá 255 ký tự; thiếu trường `file` |

## Luồng kiểm thử

Đã chạy ngày 2026-11-27 với PostgreSQL và MinIO trong compose (`/health` ok; ghi rồi đọc lại bản ghi và tệp đúng nội dung). Các lệnh `curl` nằm ở bước kiểm tra của [run-local-stack.md](../operations/run-local-stack.md). Test tự động: `cd backend && pytest`, gồm ca 404 và 422.

## Tài liệu liên quan

- [Các lớp backend](../architecture/backend-layers.md)
- Mã: `backend/app/api/v1/`
