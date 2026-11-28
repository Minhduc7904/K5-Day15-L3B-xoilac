# API quản lý ngân hàng câu hỏi và danh mục chương

Tài liệu này mô tả các endpoint admin dùng để quản lý câu hỏi Toán THPT và cây chương lớp 10–12 (issue #11). Người đọc là frontend khu quản trị (`/admin/questions`, `/admin/chapters`), pipeline học sinh #4 (định nghĩa "câu khả dụng") và nhập đề PDF #3 (dùng chung mã câu, mã chương và trạng thái duyệt). Đăng nhập, phiên và mã lỗi chung nằm ở [API xác thực](auth-api.md).

## Điều kiện gọi

- Base URL: `/api/v1/admin/questions` và `/api/v1/admin/chapters`. Local: `http://localhost:8000/api/v1/...`. Frontend gọi qua rewrite `/api/v1/*` của Next.js.
- Mọi endpoint cần phiên của **admin đang active** (cookie `examind_session` hoặc `Authorization: Bearer <token>`). Khách nhận `401 SESSION_*`, học sinh nhận `403 FORBIDDEN_ROLE`.
- Body JSON. Lỗi nghiệp vụ có dạng `{"detail": "<thông báo tiếng Việt>", "code": "<MÃ>"}`. Lỗi 422 do sai kiểu dữ liệu (thiếu trường, giá trị ngoài miền) giữ định dạng mặc định của FastAPI (`detail` là mảng lỗi theo trường).
- Không có API xoá cứng câu hỏi. "Ngừng sử dụng" là lưu trữ mềm (`questions.archived_at`, migration `0021_questions_archived_at`).

### Trạng thái câu và "câu khả dụng"

| `status` trả về | Điều kiện trong CSDL | Được #4 chọn cho đề mới? |
| --- | --- | --- |
| `PUBLISHED` | `visibility = 'PUBLISHED'` và `archived_at IS NULL` | Có |
| `DRAFT`, `PRIVATE` | `visibility` tương ứng và `archived_at IS NULL` | Không |
| `ARCHIVED` | `archived_at IS NOT NULL` (bất kể `visibility`) | Không |

Điều kiện "câu khả dụng" nằm ở một hàm duy nhất, `available_questions()` trong `backend/app/repositories/question_bank_repository.py`. Mọi truy vấn chọn câu cho đề mới của #4 (`pick`, `pick_for_section`, `practice_capacity`) dùng hàm này. Đọc lại câu đã nằm trong đề (`load_items`, `load_grading_keys`) **không** lọc theo `archived_at`, vì vậy đề nháp, lượt làm và lịch sử cũ vẫn đọc và chấm được câu đã ngừng sử dụng. #3 khi duyệt bản nháp ghi câu với `visibility = 'PUBLISHED'`, nên câu nhập từ PDF khả dụng ngay.

## Endpoint và hợp đồng

### Câu hỏi

| Method và path | Kết quả |
| --- | --- |
| `GET /admin/questions` | Danh sách phân trang, có tìm và lọc |
| `GET /admin/questions/{id}` | Chi tiết: lựa chọn/mệnh đề, đáp án, lời giải, ảnh, chương, số đề tham chiếu |
| `POST /admin/questions` | Tạo câu, lựa chọn và chương trong một giao dịch, trả `201` |
| `PUT /admin/questions/{id}` | Thay toàn bộ nội dung câu, lựa chọn và chương trong một giao dịch |
| `POST /admin/questions/{id}/archive` | Ngừng sử dụng. Gọi lại khi đã lưu trữ thì giữ mốc thời gian cũ |
| `POST /admin/questions/{id}/restore` | Khôi phục (`archived_at = NULL`) |
| `POST /admin/questions/media` | Multipart `file`: tải một ảnh (PNG, JPEG, WEBP, GIF, ≤ 5 MiB) lên MinIO, trả `201 {"media_id", "url"}` |
| `GET /admin/questions/media/{media_id}` | Trả bytes ảnh cho admin xem (ảnh `IMAGE`, `READY`) |

Tham số của `GET /admin/questions`:

| Tham số | Kiểu | Ghi chú |
| --- | --- | --- |
| `q` | chuỗi ≤ 200 | Khớp một phần `searchable_content` (ILIKE, rơi về `content` nếu cột trống). Nhập `Q00012` hoặc `12` thì khớp thêm theo mã câu |
| `grade` | 10–12 | Theo `questions.grade` |
| `chapter_id` | số | Gồm cả chương con cháu (WITH RECURSIVE) |
| `type` | `SINGLE_CHOICE` `MULTIPLE_CHOICE` `TRUE_FALSE` `SHORT_ANSWER` `ESSAY` | |
| `difficulty` | `NB` `TH` `VD` `VDC` | |
| `status` | `PUBLISHED` `DRAFT` `PRIVATE` `ARCHIVED` | Xem bảng trạng thái ở trên |
| `page`, `page_size` | `page ≥ 1`, `1 ≤ page_size ≤ 100` (mặc định 20) | Sắp theo `question_id` giảm dần |

Ví dụ phản hồi danh sách:

```json
{
  "items": [
    {
      "question_id": 2, "code": "Q00002", "content": "Cho hàm số $y=f(x)$ …",
      "type": "SINGLE_CHOICE", "difficulty": "TH", "grade": 12,
      "visibility": "PUBLISHED", "status": "PUBLISHED", "archived_at": null,
      "updated_at": "2026-11-28T09:00:00Z",
      "chapters": [{"chapter_id": 40, "code": "12C43", "name": "Ứng dụng tích phân"}]
    }
  ],
  "total": 1, "page": 1, "page_size": 20
}
```

Chi tiết (`GET /admin/questions/{id}`) có thêm các trường:

```json
{
  "correct_answer": "D",
  "solution": "$V=\\pi\\int_a^b f^2(x)\\,dx$",
  "statements": [{"statement_id": 7, "content": "$V=\\pi \\int_{a}^{b}|f(x)| d x$.", "is_correct": false, "order": 1}],
  "media_ids": [],
  "exam_count": 3,
  "created_at": "2026-11-27T08:00:00Z"
}
```

`exam_count` là số đề trong `questions_exams` đang tham chiếu câu. Đề nháp của #4 lưu câu trong JSON nên không được đếm ở đây.

Body của `POST` và `PUT`:

```json
{
  "content": "Đạo hàm của $x^2$ là ![Hình](media:12)",
  "type": "SINGLE_CHOICE",
  "difficulty": "TH",
  "grade": null,
  "visibility": "PUBLISHED",
  "correct_answer": null,
  "solution": "$(x^2)' = 2x$",
  "statements": [
    {"statement_id": 7, "content": "$2x$", "is_correct": true},
    {"content": "$x$", "is_correct": false}
  ],
  "chapter_ids": [41]
}
```

| Trường | Luật |
| --- | --- |
| `content` | Bắt buộc, 1–20.000 ký tự. Công thức `$…$`, `$$…$$`. Ảnh `![mô tả](media:ID)`, `ID` phải là ảnh `READY` có trong bảng `media` |
| `type` | `SINGLE_CHOICE`: ≥ 2 lựa chọn, đúng 1 lựa chọn đúng. `MULTIPLE_CHOICE`: ≥ 2 lựa chọn, ≥ 1 đúng. `TRUE_FALSE`: ≥ 1 mệnh đề. `SHORT_ANSWER`: cần `correct_answer`, không có lựa chọn. `ESSAY`: không có lựa chọn |
| `statements` | Tối đa 12, thứ tự trong mảng là `order`. Gửi `statement_id` để sửa tại chỗ (giữ id cho đề nháp đã tham chiếu). Bỏ `statement_id` là lựa chọn mới. Id không còn trong mảng thì bị xoá. Id của câu khác bị từ chối |
| `correct_answer` | Để trống với câu có lựa chọn thì tự suy: trắc nghiệm ra chữ cái (`"A"`, `"AC"`), đúng/sai ra chuỗi `Đ`/`S` (`"ĐSĐS"`) |
| `chapter_ids` | 1–10 chương, không lặp, phải tồn tại và cùng một khối (theo tiền tố mã chương gốc) |
| `grade` | 10–12 hoặc `null`. `null` thì suy từ chương. Có giá trị mà khác khối của chương thì bị từ chối |
| `visibility` | `PUBLISHED` (mặc định), `DRAFT`, `PRIVATE` |

Backend làm mới `searchable_content` mỗi lần tạo/sửa (nội dung + lựa chọn, bỏ tham chiếu ảnh và `$`, chữ thường) và đặt `slug = admin-<uuid>` khi tạo. Phản hồi của tạo, sửa, lưu trữ và khôi phục là chi tiết câu.

### Danh mục chương

| Method và path | Kết quả |
| --- | --- |
| `GET /admin/chapters?grade=` | Cây theo `parent_chapter_id`, sắp theo `order_in_parent` rồi `chapter_id`. Bỏ `grade` thì trả mọi khối |
| `POST /admin/chapters` | Tạo chương, trả `201` với nút vừa tạo |
| `PUT /admin/chapters/{id}` | Đổi tên, mã, slug, chương cha, thứ tự. `level` của cả nhánh được tính lại |
| `DELETE /admin/chapters/{id}` | `204`. Chỉ xoá được chương không còn chương con và không còn câu nào gắn vào |

Mỗi nút cây:

```json
{
  "chapter_id": 1, "code": "12C1", "name": "ỨNG DỤNG ĐẠO HÀM", "slug": "12c1",
  "parent_chapter_id": null, "order_in_parent": 1, "level": 0, "grade": 12,
  "question_count": 0, "subtree_question_count": 177,
  "children": [{"chapter_id": 2, "code": "12C11", "name": "Tính đơn điệu", "level": 1, "children": []}]
}
```

`question_count` là số câu gắn trực tiếp. `subtree_question_count` là số câu phân biệt gắn vào chương hoặc chương con cháu, gồm cả câu đã ngừng sử dụng. `grade` lấy theo tiền tố mã của chương gốc.

Body của `POST` và `PUT`:

```json
{"name": "Tiệm cận", "code": "12C13", "slug": null, "parent_chapter_id": 1, "order_in_parent": null}
```

| Trường | Luật |
| --- | --- |
| `code` | Dạng `<khối>C<…>` với khối 10–12, vd `12C13`. Không trùng chương khác. Cùng khối với chương cha |
| `slug` | Để trống thì tự sinh từ mã và tên (bỏ dấu), vd `12c13-tiem-can`. Không trùng |
| `parent_chapter_id` | `null` là chương gốc. Không được là chính nó hoặc một chương con cháu của nó |
| `order_in_parent` | Để trống: khi tạo hoặc đổi cha thì xếp cuối, khi sửa tại chỗ thì giữ nguyên |

Môn học (`subject_id`) lấy theo chương cha. Chương gốc lấy môn của các chương gốc cùng khối.

## Lỗi và trường hợp biên

| HTTP | `code` | Khi nào |
| --- | --- | --- |
| 401 | `SESSION_MISSING`, `SESSION_INVALID`, `SESSION_EXPIRED`, `SESSION_REVOKED` | Chưa đăng nhập hoặc phiên hết hiệu lực |
| 403 | `FORBIDDEN_ROLE` | Tài khoản học sinh gọi API admin |
| 404 | `QUESTION_NOT_FOUND` | Không có câu với `id` |
| 404 | `MEDIA_NOT_FOUND` | Ảnh không có, không phải ảnh `READY` hoặc tệp không còn trong MinIO |
| 404 | `CHAPTER_NOT_FOUND` | Không có chương, hoặc `parent_chapter_id` không tồn tại |
| 409 | `CHAPTER_CODE_TAKEN` | Mã hoặc slug chương đã được dùng, vd `"Mã chương 12C11 đã được dùng"` |
| 409 | `CHAPTER_IN_USE` | Xoá chương còn chương con hoặc còn câu (`"Chương còn 2 chương con và 5 câu hỏi gắn vào, chưa xoá được"`). Đổi khối của nhánh đang có câu |
| 422 | `INVALID_QUESTION` | Vi phạm luật theo loại câu, chương không tồn tại hoặc khác khối, ảnh không tồn tại, lựa chọn không thuộc câu |
| 422 | `INVALID_MEDIA` | Tệp tải lên không phải PNG, JPEG, WEBP, GIF hoặc lớn hơn 5 MiB |
| 422 | `CHAPTER_CYCLE` | Đặt chương làm con của chính nó hoặc của chương con cháu |
| 422 | `INVALID_CHAPTER` | Mã chương sai định dạng hoặc khác khối với chương cha |
| 422 | (mặc định FastAPI) | Sai kiểu dữ liệu, `page_size > 100`, `chapter_ids` rỗng, `type` lạ |

Ví dụ lỗi:

```json
{"detail": "Câu một đáp án cần đúng 1 lựa chọn đúng", "code": "INVALID_QUESTION"}
```

Lưu trữ và khôi phục không đổi `visibility`. Câu `DRAFT` khôi phục xong vẫn chưa khả dụng cho tới khi chuyển sang `PUBLISHED`.

## Luồng kiểm thử

Test tự động (SQLite, DDL thật của migration 0002 + cột 0021, không cần Docker), chạy trong `backend/`:

```bash
pytest -q tests/test_admin_questions.py tests/test_admin_chapters.py tests/test_question_availability.py
```

Luồng tay đầy đủ với `curl` trên stack local ([chạy bộ khung local](../operations/run-local-stack.md)). Đặt `ADMIN_EMAIL`, `ADMIN_PASSWORD` trong shell bằng tài khoản admin của máy bạn, không ghi mật khẩu vào file.

```bash
API=http://localhost:8000/api/v1
# 1. Đăng nhập admin, giữ cookie phiên
curl -s -c jar.txt -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" $API/auth/login

# 2. Tìm câu tích phân lớp 12, mức TH
curl -s -b jar.txt "$API/admin/questions?q=t%C3%ADch%20ph%C3%A2n&grade=12&difficulty=TH&page_size=5"

# 3. Sửa câu (thay 123 bằng question_id vừa tìm; giữ statement_id để sửa tại chỗ)
curl -s -b jar.txt -X PUT -H 'Content-Type: application/json' $API/admin/questions/123 -d '{
  "content": "Nội dung đã sửa $\\int_0^1 x\\,dx$", "type": "SINGLE_CHOICE", "difficulty": "TH",
  "statements": [{"content": "$\\frac12$", "is_correct": true}, {"content": "$1$", "is_correct": false}],
  "chapter_ids": [41]}'

# 4. Ngừng sử dụng
curl -s -b jar.txt -X POST $API/admin/questions/123/archive     # → "status": "ARCHIVED"

# 5. Xác nhận không còn được chọn: câu nằm trong bộ lọc ARCHIVED, không nằm trong PUBLISHED
curl -s -b jar.txt "$API/admin/questions?status=ARCHIVED"
curl -s -b jar.txt "$API/admin/questions?status=PUBLISHED&q=Q00123"   # → "total": 0
```

Kết quả mong đợi ở bước 5: câu có trong danh sách `ARCHIVED`, còn tìm trong `PUBLISHED` thì `total = 0`. Khi học sinh dựng đề mới qua [API học sinh tạo đề ôn](user-exam-api.md), câu này không xuất hiện vì #4 chọn câu qua `available_questions()`. Ngày 28/11/2026, luồng này đã được kiểm trên PostgreSQL 16 + MinIO thật bằng repository chọn câu của #4: số câu chọn được của chương `12C1`, mức `VDC`, giảm từ 14 xuống 13 sau khi lưu trữ đúng câu vừa tạo.

Ca lỗi nên thử:

```bash
# Mã chương trùng → 409 CHAPTER_CODE_TAKEN
curl -s -b jar.txt -H 'Content-Type: application/json' -d '{"name":"Trùng","code":"12C11","parent_chapter_id":1}' $API/admin/chapters
# Đặt 12C1 làm con của 12C11 (con của nó) → 422 CHAPTER_CYCLE
curl -s -b jar.txt -X PUT -H 'Content-Type: application/json' -d '{"name":"ỨNG DỤNG ĐẠO HÀM","code":"12C1","slug":"12c1","parent_chapter_id":2}' $API/admin/chapters/1
# Xoá chương còn chương con → 409 CHAPTER_IN_USE
curl -s -b jar.txt -X DELETE $API/admin/chapters/1
# Học sinh gọi API admin → 403 FORBIDDEN_ROLE; không có phiên → 401 SESSION_MISSING
curl -s $API/admin/questions
```

## Tài liệu liên quan

- [Issue #11](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/11)
- [Xác thực và phân quyền backend](../architecture/backend-auth.md) (`AdminDep`)
- [Các lớp backend](../architecture/backend-layers.md)
- [API nhập đề PDF (#3)](../ai/pdf-import/api.md) · [API mẫu cấu trúc đề (#5)](exam-templates-api.md) · [API học sinh tạo đề ôn (#4)](user-exam-api.md)
- [Kiến trúc frontend](../architecture/frontend-base.md) (khu quản trị)
- Mã nguồn: `backend/app/api/v1/admin_questions.py`, `backend/app/api/v1/admin_chapters.py`, `backend/app/usecase/admin_questions.py`, `backend/app/usecase/admin_chapters.py`
