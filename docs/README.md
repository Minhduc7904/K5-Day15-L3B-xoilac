# Mục lục tài liệu

Đây là nơi duy nhất liệt kê tài liệu trong `docs/`. Thêm file mới thì thêm một dòng vào bảng bên dưới.

## Quy ước

- Mỗi tài liệu mở đầu bằng 4 dòng: **Mục đích · Người phụ trách · Issue liên quan · Cập nhật lần cuối**.
- Đặt theo loại: `architecture/` (thiết kế), `guides/` (hướng dẫn làm việc), `api/` (hợp đồng API), `deploy/` (triển khai).
- Tên file chữ thường, nối bằng dấu gạch ngang. Không đặt dữ liệu cá nhân, khoá, mật khẩu, đường dẫn riêng của máy.

## Danh sách

| Tài liệu | Nội dung | Issue |
|---|---|---|
| [architecture/overview.md](architecture/overview.md) | Tổng quan thành phần và luồng dữ liệu | #1 |
| [architecture/backend.md](architecture/backend.md) | Các lớp backend, quy tắc phụ thuộc, nơi đặt code mới | #1 |
| [guides/local-setup.md](guides/local-setup.md) | Chạy local và kiểm tiêu chí nghiệm thu | #1 |
| [api/README.md](api/README.md) | Mẫu viết tài liệu API; chỗ đặt các tài liệu API của #3, #4, #5 | #1 |
| [deploy/README.md](deploy/README.md) | Chỗ đặt tài liệu triển khai (EC2) | #2 |
| [ai-usage.md](ai-usage.md) | Nhật ký dùng AI (khung hackathon) | — |
| [connect-model.md](connect-model.md) | Cách nối model (khung hackathon) | — |

## Đường dẫn đề xuất trong các issue → đường dẫn thực tế

| Issue đề xuất | Dùng |
|---|---|
| `docs/architecture.md` (#1) | `docs/architecture/overview.md`, `backend.md` |
| `docs/local-setup.md` (#1) | `docs/guides/local-setup.md` |
| `docs/deploy-ec2.md` (#2) | `docs/deploy/ec2.md` |
| `docs/admin-import-api.md` (#3) | `docs/api/admin-import.md` |
| `docs/user-exam-api.md` (#4) | `docs/api/user-exam.md` |
| `docs/exam-templates-api.md` (#5) | `docs/api/exam-templates.md` |
