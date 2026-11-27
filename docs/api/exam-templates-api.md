# API mẫu cấu trúc đề thi

Admin tạo, sửa và duyệt mẫu cấu trúc đề (giữa kỳ, cuối kỳ, tốt nghiệp THPT, HSA, TSA). Pipeline học sinh (#4) dùng `GET /exam-templates/lookup` để tìm mẫu **đã duyệt** khi học sinh muốn ôn theo kỳ thi. Thuộc issue #5.

## Điều kiện gọi

- Base URL local: `http://localhost:8000/api/v1`. Tài liệu tự sinh: `http://localhost:8000/docs`.
- Dữ liệu gửi và nhận dạng JSON.
- **Chưa có xác thực.** Khi thiết kế Auth #8 được chốt, các route tạo, sửa, duyệt và xem danh sách sẽ chỉ dành cho admin. `GET /exam-templates/lookup` dành cho backend pipeline học sinh.
- Cần migration `0005_exam_templates` (`alembic upgrade head`).

## Mô hình dữ liệu

| Trường | Kiểu | Bắt buộc | Ghi chú |
| --- | --- | --- | --- |
| `name` | chuỗi 1–255 | Có | Tên mẫu |
| `exam_type` | `GK1` `GK2` `CK1` `CK2` `THPT` `HSA` `TSA` | Có | Cùng mã với `exams.type_of_exam` |
| `grade` | 10–12 hoặc `null` | Theo luật | Bắt buộc với giữa kỳ, cuối kỳ. Chỉ `12` hoặc `null` với `THPT`, `HSA`, `TSA` |
| `version_label` | chuỗi ≤ 50 | Không | Năm hoặc phiên bản, ví dụ `2025` |
| `duration_minutes` | 1–300 | Không | |
| `source` | chuỗi ≤ 2000 | Khi duyệt | Văn bản, đề minh hoạ hoặc ma trận làm căn cứ. Thiếu thì không duyệt được |
| `description` | chuỗi ≤ 5000 | Không | |
| `sections` | 1–20 phần | Có | Xem bảng dưới |

Mỗi phần (`sections[]`):

| Trường | Kiểu | Bắt buộc | Ghi chú |
| --- | --- | --- | --- |
| `order` | 1–50 | Có | Không trùng trong một mẫu; phản hồi sắp theo `order` |
| `title` | chuỗi 1–255 | Có | |
| `question_type` | `SINGLE_CHOICE` `MULTIPLE_CHOICE` `TRUE_FALSE` `SHORT_ANSWER` `ESSAY` | Có | Cùng mã với `questions.type` |
| `count` | 1–100 | Có | Số câu của phần |
| `points_per_question` | > 0, ≤ 10 | Không | |
| `difficulty_distribution` | `{"NB"|"TH"|"VD"|"VDC": số câu}` | Không | Nếu có, tổng phải bằng `count` |
| `chapter_codes` | danh sách mã chương | Không | Dạng `12C1`. Với giữa kỳ, cuối kỳ, chương phải thuộc đúng khối của đề |

Phản hồi thêm `template_id`, `total_questions` (tổng `count`, tối đa 200), `status` (`DRAFT` hoặc `APPROVED`), `approved_at`, `created_at`, `updated_at`.

## Endpoint và hợp đồng

### POST /exam-templates

Tạo mẫu mới ở trạng thái `DRAFT`. Phản hồi `201` với mẫu vừa tạo.

```json
// request
{
  "name": "Giữa kỳ 1 lớp 11",
  "exam_type": "GK1",
  "grade": 11,
  "duration_minutes": 90,
  "source": "Ma trận đề của tổ Toán",
  "sections": [
    {"order": 1, "title": "Phần I. Trắc nghiệm", "question_type": "SINGLE_CHOICE", "count": 10,
     "points_per_question": 0.25, "difficulty_distribution": {"NB": 4, "TH": 4, "VD": 2},
     "chapter_codes": ["11C1", "11C2"]}
  ]
}
// response 201 (rút gọn)
{"template_id": 1, "status": "DRAFT", "total_questions": 10, "approved_at": null, "...": "..."}
```

Ví dụ trên chỉ minh hoạ định dạng, không phải cấu trúc đề chính thức.

### GET /exam-templates

Danh sách cho admin, mọi trạng thái, mới sửa trước, tối đa 100. Bộ lọc tuỳ chọn: `status`, `exam_type`, `grade`.

### GET /exam-templates/{template_id}

Một mẫu. `404` nếu không có.

### PUT /exam-templates/{template_id}

Thay toàn bộ nội dung mẫu, body giống `POST`. Mẫu giữ nguyên trạng thái:

- Mẫu `DRAFT`: kiểm luật thường.
- Mẫu `APPROVED`: phải vẫn đạt điều kiện duyệt (có `source`). Nếu đạt, mẫu vẫn `APPROVED` và lượt `lookup` kế tiếp trả ngay cấu trúc mới. Nếu không đạt, trả `422` và mẫu không đổi.

### POST /exam-templates/{template_id}/approve

Duyệt mẫu: kiểm lại toàn bộ luật cùng điều kiện duyệt, rồi đặt `APPROVED` và `approved_at`. Gọi lại với mẫu đã duyệt thì trả mẫu như cũ (không lỗi).

### GET /exam-templates/lookup

Hợp đồng đọc cho pipeline học sinh (#4). **Chỉ trả mẫu `APPROVED`**, mới sửa trước.

| Tham số | Bắt buộc | Ghi chú |
| --- | --- | --- |
| `exam_type` | Có | Như trên |
| `grade` | Không | Trả mẫu đúng khối và mẫu không ghi khối (`grade = null`) |
| `version_label` | Không | Khớp đúng chuỗi |

Kết quả là mảng, có thể rỗng hoặc nhiều mẫu. Pipeline học sinh quyết định:

| Số mẫu | Hành vi của agent |
| --- | --- |
| 0 | Báo chưa có cấu trúc đã xác thực cho kỳ thi này, đề nghị ôn theo chương (ca B09) |
| 1 | Đưa mẫu vào bản xem trước để học sinh xác nhận |
| ≥ 2 | Hỏi lại học sinh (khối, học kỳ, năm) để chọn một |

## Lỗi và trường hợp biên

| Mã | Khi nào |
| --- | --- |
| 404 | Không có mẫu với `template_id` |
| 422 (lỗi hình dạng) | Sai kiểu, giá trị ngoài miền (ví dụ `exam_type` lạ, `sections` rỗng), thiếu `exam_type` khi gọi `lookup`. `detail` theo định dạng mặc định của FastAPI |
| 422 (lỗi nghiệp vụ) | Vi phạm luật liên trường. `detail` là `{"message": "Mẫu không hợp lệ", "errors": ["...", "..."]}`, mỗi phần tử là một lý do đọc được cho admin |

Các luật nghiệp vụ: giữa kỳ, cuối kỳ phải có khối; `THPT`, `HSA`, `TSA` chỉ khối 12 hoặc để trống; `order` không trùng; tổng số câu ≤ 200; phân bố độ khó cộng đúng bằng `count`; mã chương đúng định dạng và (với giữa kỳ, cuối kỳ) đúng khối; duyệt cần `source`.

## Luồng kiểm thử

Test tự động: `cd backend && pytest tests/test_exam_templates.py` (chạy bằng SQLite trong bộ nhớ, không cần Docker). Các ca đã có:

1. Tạo mẫu → `DRAFT`, `total_questions` đúng, phần sắp theo `order`.
2. Mẫu nháp không xuất hiện trong `lookup`. Duyệt khi thiếu `source` → `422`, vẫn `DRAFT`. Thêm `source` rồi duyệt → `APPROVED`, `lookup` trả mẫu.
3. Sửa hợp lệ mẫu đã duyệt → vẫn `APPROVED`, `lookup` trả cấu trúc mới ngay.
4. Sửa mẫu đã duyệt làm mất `source` → `422`, mẫu không đổi.
5. `lookup` lọc theo loại kỳ thi và khối; mẫu `THPT` không ghi khối khớp khi hỏi khối 12.
6. Các ca `422` nghiệp vụ, `422` hình dạng và `404`.

Chưa kiểm với PostgreSQL thật. Đã kiểm SQL của migration bằng `alembic upgrade 0002:0005_exam_templates --sql`.

## Tài liệu liên quan

- [Các lớp backend](../architecture/backend-layers.md)
- Issue #5 (mẫu cấu trúc đề) và #4 (pipeline học sinh)
- Mã: `backend/app/api/v1/exam_templates.py`, `backend/app/usecase/exam_templates.py`, `backend/app/usecase/exam_template_rules.py`
