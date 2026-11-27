# API học sinh tạo đề ôn

Học sinh chat với agent để nhận đề xuất cấu trúc đề (bản xem trước), chỉnh bằng lời hoặc trên giao diện, xác nhận, rồi nhận đề nháp ghép từ câu đã duyệt. Dành cho frontend (#9) và người tích hợp. Thuộc issue #4.

## Điều kiện gọi

- Base URL local: `http://localhost:8000/api/v1`. Tài liệu tự sinh: `http://localhost:8000/docs`.
- Dữ liệu gửi dạng JSON. Tin nhắn chat trả về luồng **SSE** (`text/event-stream`).
- Cần migration `0004` (`alembic upgrade head`) và dữ liệu nền (bảng `questions`, `chapters`, `statements`).
- **Chưa có xác thực.** Khi tạo phiên, client gửi `student_ref` (mã học sinh). Khi Auth #8 xong, học sinh lấy từ phiên đăng nhập và mỗi học sinh chỉ đọc được phiên của mình, kể cả kết nối SSE.

## Khái niệm

**Bản xem trước** (`preview`): một phiên có đúng một bản, chứa cấu trúc đề:

```json
{
  "chapters": [{"code": "12C1", "count": 10}],
  "difficulty_weights": {"NB": 0.2, "TH": 0.4, "VD": 0.4},
  "excluded_difficulties": []
}
```

Số câu mỗi mức của từng chương được chia từ `count` theo `difficulty_weights` (bỏ mức trong `excluded_difficulties`). Tối đa 50 câu, 5 chương.

**Trạng thái bản xem trước:**

| Trạng thái | Nghĩa | Đi tiếp |
| --- | --- | --- |
| `PROPOSED` | Agent vừa đề xuất | Chỉnh → `EDITED`; xác nhận → dựng đề |
| `EDITED` | Đã chỉnh (chat hoặc API) | Chỉnh tiếp; xác nhận → dựng đề |
| `CONFIRMED` | Đang dựng đề (trạng thái trung gian) | |
| `BUILT` | Đã có đề nháp | Chỉnh → `EDITED` rồi xác nhận lại để dựng đề mới |

**`version`** tăng mỗi lần bản xem trước đổi. Mọi lệnh chỉnh và xác nhận qua API phải gửi `version` client đang thấy; lệch thì nhận `409` kèm `current_version` để tải lại. Nhờ vậy chat và giao diện không ghi đè nhau.

**Đề nháp** (`draft`): tên dạng `Đề ôn luyện ngày dd/mm/yyyy` (giờ Việt Nam). Mỗi câu có mã `Q` + 5 chữ số, chương, độ khó, loại, nội dung và các lựa chọn. **Không bao giờ có đáp án, cờ đúng/sai hay lời giải.** Chỉ lấy câu có `questions.visibility = 'PUBLISHED'` (giả định "đã duyệt", chờ #3, #11 xác nhận). Ngân hàng thiếu câu thì đề có ít câu hơn và `shortages` ghi rõ thiếu ở đâu.

## Endpoint và hợp đồng

| Method | Path | Việc |
| --- | --- | --- |
| POST | `/exam-chat/sessions` | Tạo phiên |
| GET | `/exam-chat/sessions/{id}` | Đọc phiên: tin nhắn, bản xem trước, đề nháp mới nhất |
| POST | `/exam-chat/sessions/{id}/messages` | Gửi tin nhắn, nhận SSE |
| GET | `/exam-chat/sessions/{id}/preview` | Đọc bản xem trước |
| PATCH | `/exam-chat/sessions/{id}/preview` | Chỉnh bản xem trước từ giao diện |
| POST | `/exam-chat/sessions/{id}/preview/confirm` | Xác nhận và dựng đề nháp |
| GET | `/exam-chat/sessions/{id}/draft` | Đề nháp mới nhất |

### POST /exam-chat/sessions

```json
// request
{"student_ref": "HS01"}
// response 201
{"session_id": 1, "student_ref": "HS01", "created_at": "2026-11-28T01:00:00Z"}
```

### POST /exam-chat/sessions/{id}/messages (SSE)

Body `{"text": "..."}` (1–2000 ký tự). Phản hồi `200`, `Content-Type: text/event-stream`. Mỗi sự kiện có dạng:

```
event: <tên>
data: <JSON>

```

Thứ tự sự kiện trong một lượt:

| Thứ tự | Sự kiện | Số lần | `data` |
| --- | --- | --- | --- |
| 1 | `message` | ≥ 1 | `{"delta": "một đoạn chữ"}`. Ghép các `delta` theo thứ tự thành câu trả lời |
| 2 | `preview` | 0–1 | Bản xem trước mới (cùng dạng `GET .../preview`), chỉ khi lượt này đổi nó |
| 3 | `draft` | 0–1 | Đề nháp (cùng dạng `GET .../draft`), chỉ khi lượt này dựng đề |
| 4 | `done` | 1 | `{"preview_version": 3}` hoặc `null` |
| thay 1–4 | `error` | 1 | `{"code": "internal_error", "message": "..."}` khi xử lý lỗi; luồng kết thúc ngay |

Phiên không tồn tại trả `404` thường (không mở luồng).

Ví dụ một lượt đề xuất:

```
event: message
data: {"delta": "Đề xuất cấu trúc đề ôn (chưa tạo đề):\n"}

event: message
data: {"delta": "- 12C1 ỨNG DỤNG ĐẠO HÀM: 10 câu (2 nhận biết, 4 thông hiểu, 4 vận dụng)\n"}

event: preview
data: {"session_id": 1, "mode": "CHAPTER", "status": "PROPOSED", "version": 1, "structure": {...}, "reason": "Lý do: ...", "updated_at": "..."}

event: done
data: {"preview_version": 1}
```

Agent hiểu các loại tin nhắn (bằng quy tắc, chưa gọi model):

| Học sinh nhắn | Agent làm |
| --- | --- |
| Ôn chương hay sai, có thể kèm số câu | Tính tỉ lệ đúng theo chương từ lịch sử làm bài, đề xuất chương yếu nhất (hai chương nếu cách nhau ≤ 10 điểm %) kèm số liệu sai/tổng |
| Nêu mã chương, số câu, độ khó ("đổi sang 12C4, 6 câu, không lấy vận dụng cao", "giảm còn 8 câu") | Sửa bản xem trước hiện tại, hoặc tạo mới nếu chưa có |
| Xác nhận ("xác nhận", "tạo đề", có thể kèm cấu trúc) | Xác nhận và dựng đề nháp |
| Theo kỳ thi | Hỏi lại nếu thiếu loại kỳ thi; chưa có mẫu đã duyệt thì nói rõ và đề nghị ôn theo chương |
| Chưa có lịch sử, lịch sử mâu thuẫn, chương không có trong danh mục, vượt 50 câu | Nói rõ, hỏi lại, không đoán và không bịa câu |
| Bỏ qua hướng dẫn, đòi đáp án, sửa điểm, xin đáp án để chép, ngoài môn Toán | Từ chối và gợi ý việc làm được |

### PATCH /exam-chat/sessions/{id}/preview

Chỉnh từ giao diện, cùng luật với chat. Trường bỏ trống là giữ nguyên.

```json
// request
{
  "version": 2,
  "edit": {
    "total": 8,
    "chapter_codes": ["12C4"],
    "chapter_counts": {"12C1": 5, "12C4": 3},
    "only_difficulty": "TH",
    "exclude_difficulties": ["VDC"],
    "difficulty_counts": {"TH": 3, "VD": 2}
  }
}
```

| Trường `edit` | Tác dụng |
| --- | --- |
| `total` | Đổi tổng số câu, giữ tỉ lệ giữa các chương |
| `chapter_codes` | Thay danh sách chương, chia đều tổng số câu |
| `chapter_counts` | Đặt số câu từng chương (ưu tiên hơn `chapter_codes`) |
| `only_difficulty` | Chỉ lấy một mức |
| `exclude_difficulties` | Bỏ các mức |
| `difficulty_counts` | Đặt tỉ lệ độ khó theo số câu |

Phản hồi `200` là bản xem trước mới (`status = EDITED`, `version` tăng 1).

### POST /exam-chat/sessions/{id}/preview/confirm

```json
// request
{"version": 3}
// response 200
{"preview": {"status": "BUILT", "version": 5, "...": "..."},
 "draft": {"draft_id": 1, "title": "Đề ôn luyện ngày 28/11/2026", "items": [...], "shortages": [...], "...": "..."},
 "message": "Đề ôn luyện ngày 28/11/2026: BẢN NHÁP đề ôn ..."}
```

`draft` là `null` khi ngân hàng không có câu nào phù hợp; khi đó bản xem trước về `EDITED` để chỉnh lại.

Một câu trong `items`:

```json
{"order": 1, "question_id": 20, "code": "Q00020", "chapter": "12C4", "difficulty": "TH",
 "type": "SINGLE_CHOICE", "content": "...", "statements": [{"order": 1, "content": "..."}]}
```

## Lỗi và trường hợp biên

| Mã | Khi nào |
| --- | --- |
| 404 | Không có phiên; phiên chưa có bản xem trước; chưa có đề nháp |
| 409 | `version` lệch (`detail.current_version` là bản mới nhất); xác nhận bản đã `BUILT` |
| 422 | Sai kiểu dữ liệu, tin nhắn rỗng; cấu trúc vi phạm luật (`detail.errors`: chương không có trong danh mục, quá 50 câu, loại hết mức độ khó, chương lặp) |

## Luồng kiểm thử

Test tự động: `cd backend && pytest tests/test_exam_chat_api.py tests/test_exam_chat_rules.py` (SQLite trong bộ nhớ, ngân hàng và lịch sử tự dựng). Ca trọn luồng đã kiểm:

1. HS01 nhắn "Ra đề ôn chương em hay sai" → SSE có `message`, `preview` (12C1, 10 câu, `PROPOSED`), `done`; chưa có mã câu.
2. "giảm còn 4 câu" → `EDITED`, version 2.
3. `PATCH` với version 1 → `409`; với version 2 đổi sang 12C4 chỉ TH → version 3.
4. "Em xác nhận, tạo đề nháp" → dùng bản đã sửa qua API, đề nháp 3 câu 12C4 và `shortages` báo thiếu 1 câu; không có đáp án.
5. Các ca hỏi lại hoặc từ chối không tạo bản xem trước hay mã câu.

Chưa kiểm với PostgreSQL thật và dữ liệu nền. Đã kiểm SQL của migration bằng `alembic upgrade 0002:0004 --sql`.

## Phần còn chờ

| Phần | Chờ | Hiện tại |
| --- | --- | --- |
| Lịch sử làm bài thật | Chưa có bảng kết quả làm bài | `NoHistory`: agent nói chưa có lịch sử và hỏi chương |
| Ôn theo mẫu kỳ thi | #5 merge | `NoTemplates`: agent nói chưa có cấu trúc đã xác thực |
| Diễn đạt bằng model thật | Chốt nhà cung cấp và key | Trả văn bản dựng bằng code, chia theo dòng |
| Quyền học sinh | Auth #8 | `student_ref` do client gửi |
| Định nghĩa "câu đã duyệt" | #3, #11 | `visibility = 'PUBLISHED'` |

Ba nguồn đầu là chỗ cắm trong `backend/app/api/deps.py` (`get_student_history`, `get_exam_template_source`, `get_reply_writer`).

## Tài liệu liên quan

- [Các lớp backend](../architecture/backend-layers.md)
- API mẫu cấu trúc đề: `docs/api/exam-templates-api.md` (#5, hiện ở nhánh `feat/issue-5-exam-templates`, chưa merge)
- Mã: `backend/app/api/v1/exam_chat.py`, `backend/app/usecase/exam_chat.py`, `backend/app/usecase/exam_preview_rules.py`, `backend/app/usecase/exam_chat_intent.py`
