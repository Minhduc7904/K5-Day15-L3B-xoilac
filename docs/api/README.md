# Tài liệu API

**Mục đích:** nơi đặt hợp đồng API của từng issue và mẫu để viết · **Người phụ trách:** theo từng issue · **Issue:** #1 (mẫu), #3, #4, #5 · **Cập nhật:** 2026-11-27

Dự kiến:

| File | Issue |
|---|---|
| `admin-import.md` | #3 nhập PDF |
| `user-exam.md` | #4 chat và tạo đề |
| `exam-templates.md` | #5 mẫu cấu trúc đề |

## Mẫu cho mỗi endpoint

Ghi đủ: method và path · quyền truy cập · tham số · ví dụ request · ví dụ response · mã lỗi.

```
### POST /api/v1/sample-items
Quyền: công khai (chỉ là mẫu)
Request:  {"name": "de mau"}
Response 201: {"id": 1, "name": "de mau", "created_at": "2026-11-27T12:13:20Z"}
Lỗi: 422 khi name rỗng
```

Tài liệu API tự sinh luôn có ở `/docs` khi chạy backend; file ở đây ghi thêm ngữ cảnh, trạng thái xử lý và ví dụ trọn luồng.
