# API học sinh tạo đề ôn

Học sinh chat với agent để nhận đề xuất cấu trúc đề (bản xem trước), chỉnh bằng lời hoặc trên giao diện, xác nhận, rồi nhận đề nháp ghép từ câu đã duyệt. Dành cho frontend (#9) và người tích hợp. Thuộc issue #4.

## Luồng chat thật

Bật `EXAM_CHAT_LIVE=true` trên backend sau migration `0014_exam_chat_images`. Cấu hình
`OPENAI_API_KEY` và tùy chọn `EXAM_CHAT_MODEL`. Frontend luôn gọi luồng này, không còn cờ riêng. Giao diện dùng tài khoản và hồ sơ #36.

- Model chọn công cụ từ hội thoại, khối lớp, kỳ thi và mục tiêu điểm. Server tự tra dữ liệu và kiểm tra thao tác.
  Khi chọn chương cha cho đề tự chọn, server phân bổ vào chương con. Nếu người dùng chọn một chương con,
  chỉ lấy câu trong phạm vi đó. Đề từ mẫu giữ cấu trúc mẫu đã duyệt. Giới hạn chung là 50 câu.
- `GET /exam-chat/sessions` liệt kê phiên của tài khoản. `GET /exam-chat/sessions/{id}/transcript` nhận
  `before` là mã tin nhắn và `limit` là số tin để tải lịch sử cũ hơn. `GET /exam-chat/chapters` trả danh mục
  theo mã với tên và `parent_code`.
- `PATCH /exam-chat/sessions/{id}` đổi tên đoạn chat (`{"title": "..."}`, 1–80 ký tự, không để trống), trả phần tử như
  `GET /exam-chat/sessions`. `DELETE /exam-chat/sessions/{id}` trả `204` và ẩn phiên khỏi danh sách; dữ liệu và
  đề nháp đã dựng vẫn còn nên "Đề của tôi" và lượt làm bài không đổi. Người khác nhận `404`, như phiên không tồn tại.
  Tên do học sinh đặt ưu tiên hơn tên lấy từ tin nhắn đầu.
- `edit.title` (tối đa 120 ký tự) đặt tên đề cho bản xem trước theo chương hoặc theo mẫu. Khi dựng, tên này thành
  tên đề nháp; không đặt thì server tự đặt "Đề ôn luyện ngày …". Đổi tên không làm đổi cấu trúc nên không đặt lại ma trận.
- `plan` trong body tin nhắn (tuỳ chọn) là tổng quan học sinh vừa chỉnh: `chapter_counts`, `type_counts` (mỗi số 1–50) và
  `difficulty_counts` (0–50). Server đưa nó vào ngữ cảnh của agent để phân bổ lại thành ma trận chi tiết theo chương con;
  kết quả vẫn qua cùng bước kiểm tra như mọi chỉnh sửa khác.
- `PATCH /exam-chat/sessions/{id}/preview` chấp nhận `edit.rows` gồm `chapter`, `difficulty`, `type`, `count`
  cho đề tự chọn. Bản xem trước có thể kèm `operation` đổi câu hoặc dựng lại bộ câu. Sự kiện SSE
  `preview` mang `null` khi học sinh bỏ bản xem trước chưa dựng.
- Xác nhận lần đầu tốn 100 credit khi lưu thành công. Dùng lại `draft_id` cho các lần chỉnh hoặc dựng lại.
  Nếu thiếu câu, phản hồi có `preview.offer` chứa `requested`, `count` và `shortages`, chưa lưu đề hay
  tính phí. Gửi lại phiên bản mới kèm `accepted_count` khi học sinh đồng ý đúng số đã báo.
  Hết credit trả `402 INSUFFICIENT_CREDITS` và giữ preview.
- `GET /exam-chat/drafts` liệt kê đề hiện hành của tài khoản. `GET /exam-chat/drafts/{id}` đọc nội dung đề và
  `GET /exam-chat/drafts/{id}/media/{media_id}` đọc ảnh trong đề. Chủ đề và kết quả làm bài cũ không được
  suy ra từ dữ liệu thử. Đề hỗ trợ xem, in và làm trực tuyến qua [API lượt làm bài](online-exam-attempts-api.md).

### Ôn theo lịch sử đã chấm

Gửi “Tạo đề ôn tiếp” qua endpoint tin nhắn đang dùng. Agent lấy khối trong hồ sơ hoặc phạm vi học sinh chọn và chỉ đọc lượt của tài khoản đăng nhập. Mỗi lần yêu cầu mới đọc lại tối đa năm lượt đã chấm trong 30 ngày, xếp theo thời điểm chấm rồi mã lượt. Phản hồi tóm tắt bài vừa làm và các lượt trước trong khoảng này.

| Số câu đã làm theo chương cha | Cách diễn giải |
| --- | --- |
| 0 | Chưa luyện trong khoảng đang xét |
| 1–4 | Ít dữ liệu, kể cả sai 1/1 |
| Ít nhất 5 và sai từ 50% | Chương yếu cần củng cố |
| Ít nhất 5 và sai dưới 50% | Có đủ dữ liệu để ôn cân bằng |

Chỉ trạng thái `correct` tính đúng. `wrong` và `partial` tính sai. Câu bỏ qua được đếm riêng và không tính vào mẫu số. Server gộp theo chương cha và loại mục thiếu kết quả hoặc nhãn chương rõ ràng. Lượt thiếu căn cứ hoặc có kết quả trái nhau trong cùng lượt dẫn tới câu hỏi chọn chương hoặc gợi ý làm bài ngắn. Các ngưỡng nằm trong `backend/app/service/exam_chat_sources.py`.

Model nhận thống kê tổng hợp, phạm vi, ràng buộc và số câu đã duyệt theo ô. Kết quả là các nhóm chương, độ khó, dạng câu, số lượng, mã căn cứ và mục đích luyện. Server kiểm số liệu và ghép thử câu phân biệt trước khi gửi `preview`. Kho thiếu thì tin nhắn nêu phần thiếu để học sinh sửa. Nếu kho thay đổi sau khi xem trước, dùng cơ chế `offer` và xác nhận số câu rút gọn đang có. Bước dựng và định dạng sự kiện SSE dùng hợp đồng hiện có.

#### Kiểm chứng CP3 #41

Ca live ngày 28/11/2026 dùng hai tài khoản lớp 12 tự tạo và nộp bài qua API thật trong cơ sở dữ liệu kiểm thử.

| Ca | Kết quả |
| --- | --- |
| Cùng yêu cầu “Tạo đề ôn tiếp 1 câu thông hiểu” | Tài khoản A nhận `12C11` vì sai 6/6 câu ở chương cha `12C1`. Tài khoản B nhận `12C4` vì sai 6/6 câu ở chương đó. |
| Có lượt chấm mới trong phiên chat của A | Sau khi A làm đúng một lượt ở `12C1` và nộp hai lượt ở `12C4`, đề xuất chuyển sang `12C4`. |
| Xem trước, chỉnh và xác nhận | A chỉnh từ một thành hai câu rồi xác nhận. Đề nháp chứa hai câu đã duyệt và ẩn dữ liệu đáp án. |

Ba lời gọi đề xuất dùng `gpt-5.4-mini-2026-03-17`. API ghi lần lượt 830, 830 và 843 token vào, cùng 52 token ra mỗi lần. Các ca lịch sử rỗng, 1/1, chưa luyện, mâu thuẫn, kho thiếu, đổi phiên bản, chặn truy cập chéo và chỉnh qua chat chạy trong bộ test thường.

Chạy lại ca live từ thư mục `backend/` bằng PowerShell với khóa model đã cấu hình.

```powershell
$env:EXAMIND_CP3_LIVE = '1'
..\.venv\Scripts\python.exe -m pytest -q tests/test_personalization_chat.py -k configured_provider --log-cli-level=INFO
$env:EXAMIND_CP3_LIVE = $null
```

### Ảnh trong chat

- `POST /exam-chat/sessions/{id}/messages/with-images` nhận multipart với trường lặp `images`, văn bản
  `text` có thể để trống và `version` là bản xem trước đang thấy (0 nếu chưa có). Tối đa 4 ảnh PNG, JPEG
  hoặc WebP, tổng 4 MB. Phản hồi dùng cùng SSE với tin nhắn văn bản.
- Backend lưu ảnh vào bucket MinIO riêng của ứng dụng và lưu metadata theo tin nhắn. `messages[].attachments`
  trả ID, vị trí và MIME. `GET /exam-chat/sessions/{id}/attachments/{attachment_id}` chỉ trả ảnh cho chủ phiên.
- Dùng `MISTRAL_API_KEY` và `OCR_MODEL` của service nhập đề PDF. Nếu chưa có khóa hoặc OCR chưa dùng được,
  ảnh vẫn được lưu và chatbot báo trạng thái. Agent chỉ dùng trích đoạn OCR đã kiểm tra thuộc Toán THPT để
  lập đề. Không dùng ảnh để xác nhận dựng đề và không lưu nguyên văn OCR vào lịch sử chat.

Các ví dụ phía dưới mô tả hợp đồng cơ sở của issue #4. Phần xác nhận thiếu câu và cập nhật cùng đề hiện hành
ở trên áp dụng khi bật luồng thật.

## Điều kiện gọi

- Base URL local: `http://localhost:8000/api/v1`. Tài liệu tự sinh: `http://localhost:8000/docs`.
- Dữ liệu gửi dạng JSON. Tin nhắn chat trả về luồng **SSE** (`text/event-stream`).
- Cần migration `0006_exam_chat` (`alembic upgrade head`) và dữ liệu nền (bảng `questions`, `chapters`, `statements`).
- **Quyền** (Auth #8, cookie phiên hoặc `Authorization: Bearer`): mọi route `/exam-chat` cần đăng nhập **vai trò học sinh**. Chưa đăng nhập trả `401`; tài khoản admin trả `403` với `code = "FORBIDDEN_ROLE"` (định dạng lỗi chung của auth: `{"detail": "...", "code": "..."}`). Học sinh **chỉ thấy phiên của chính mình**: phiên của người khác, kể cả khi mở SSE, trả `404` như không tồn tại. `student_ref` lấy từ tài khoản (`U<user_id>`), giá trị client gửi bị bỏ qua.

## Khái niệm

**Bản xem trước** (`preview`): một phiên có đúng một bản, ở một trong hai chế độ, phân biệt bằng `mode` của preview và `structure.kind`.

**Chế độ ôn theo chương** (`mode = CHAPTER`, `structure.kind = "CHAPTER"`): chương yếu từ lịch sử làm bài, hoặc chương học sinh chọn. Học sinh chỉnh tự do.

```json
{
  "kind": "CHAPTER",
  "chapters": [{"code": "12C1", "count": 10}],
  "difficulty_weights": {"NB": 0.2, "TH": 0.4, "VD": 0.4},
  "excluded_difficulties": []
}
```

Số câu mỗi mức của từng chương được chia từ `count` theo `difficulty_weights` (bỏ mức trong `excluded_difficulties`). Tối đa 50 câu.

**Chế độ ôn theo mẫu kỳ thi** (`mode = EXAM_TEMPLATE`, `structure.kind = "EXAM_TEMPLATE"`): bản chụp của một mẫu **đã duyệt** từ #5. Mẫu cố định các phần, loại câu, số câu và phân bố độ khó. Học sinh **chỉ được thu hẹp chương** trong phạm vi mẫu; chỉnh khác bị từ chối kèm lý do (xem "Lỗi").

```json
{
  "kind": "EXAM_TEMPLATE",
  "template_id": 7, "template_name": "Cuối kỳ 1 lớp 12", "exam_type": "CK1", "grade": 12,
  "version_label": "2025", "duration_minutes": 90, "source": "Ma trận đề của tổ Toán",
  "sections": [
    {"order": 1, "title": "Phần I. Trắc nghiệm", "question_type": "SINGLE_CHOICE", "count": 6,
     "points_per_question": 0.25, "difficulty_distribution": {"TH": 4, "VD": 2},
     "allowed_chapters": ["12C1", "12C4"], "chapters": null}
  ]
}
```

`allowed_chapters` là phạm vi của mẫu (`null` là không giới hạn chương, khi đó lọc theo khối của mẫu). `chapters` là phạm vi học sinh đã thu hẹp (`null` là dùng cả phạm vi mẫu). `difficulty_distribution` là `null` thì lấy mọi mức độ khó.

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
| PATCH | `/exam-chat/sessions/{id}` | Đổi tên phiên |
| DELETE | `/exam-chat/sessions/{id}` | Ẩn phiên khỏi danh sách |
| GET | `/exam-chat/sessions/{id}` | Đọc phiên: tin nhắn, bản xem trước, đề nháp mới nhất |
| POST | `/exam-chat/sessions/{id}/messages` | Gửi tin nhắn, nhận SSE |
| GET | `/exam-chat/sessions/{id}/preview` | Đọc bản xem trước |
| PATCH | `/exam-chat/sessions/{id}/preview` | Chỉnh bản xem trước từ giao diện |
| POST | `/exam-chat/sessions/{id}/preview/confirm` | Xác nhận và dựng đề nháp |
| GET | `/exam-chat/sessions/{id}/draft` | Đề nháp mới nhất |

### POST /exam-chat/sessions

```json
// request (đã đăng nhập vai trò học sinh; body có thể để trống)
{}
// response 201
{"session_id": 1, "student_ref": "U12", "created_at": "2026-11-28T01:00:00Z"}
```


### POST /exam-chat/sessions/{id}/messages (SSE)

Body `{"text": "...", "version": 2, "plan": {...}}` (`text` 1–2000 ký tự; `version` và `plan` tuỳ chọn). Phản hồi `200`, `Content-Type: text/event-stream`. Mỗi sự kiện có dạng:

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
| Theo kỳ thi ("ôn thi cuối kỳ 1 lớp 12", "đề thi tốt nghiệp THPT 2025") | Nhận diện loại kỳ thi (`GK1`, `GK2`, `CK1`, `CK2`, `THPT`, `HSA`, `TSA`), khối, năm, rồi tra mẫu đã duyệt: **0 mẫu** thì nói chưa có cấu trúc đã xác thực và đề nghị ôn theo chương; **nhiều mẫu** thì liệt kê và hỏi thêm khối hoặc năm; **1 mẫu** thì tạo bản xem trước theo mẫu. Thiếu loại kỳ thi (vd "cuối kỳ" mà không nói học kỳ) thì hỏi lại |
| Đang ở bản theo mẫu, nhắn thu hẹp chương ("chỉ ôn 12C4") | Thu hẹp phạm vi chương trong giới hạn mẫu |
| Đang ở bản theo mẫu, nhắn đổi số câu hoặc độ khó | Từ chối vì xung đột ràng buộc của mẫu, giữ nguyên bản xem trước, gợi ý chuyển sang ôn theo chương |
| "ôn theo chương ...", hoặc ôn chương hay sai | Chuyển sang chế độ ôn theo chương |
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

Với bản theo mẫu kỳ thi, chỉ `chapter_codes` được nhận (thu hẹp chương, phải nằm trong phạm vi mẫu và không vượt khối của mẫu). `total` khác tổng của mẫu, `chapter_counts` và các trường độ khó trả `422` với `detail.code = "TEMPLATE_CONFLICT"`.

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
{"order": 1, "question_id": 20, "code": "Q00020", "chapter": "12C4", "chapter_codes": ["12C4"],
 "difficulty": "TH", "type": "SINGLE_CHOICE", "content": "...", "statements": [{"order": 1, "content": "..."}],
 "section_order": null, "section_title": null, "points": null}
```

Đề theo mẫu kỳ thi có thêm `section_order` và `section_title`. `items[].points` giữ điểm gốc do mẫu khai báo. Với câu chưa có điểm sẵn, trường này chứa điểm được phân bổ. `items[].max_points` là điểm dùng khi chấm. Tổng điểm tối đa của đề là `max_score = 10`. Với đề theo chương, `type_point_weights` mặc định là 30/40/30 cho trắc nghiệm, Đúng/Sai và TLN. Trường này có thể sửa trong bản xem trước. Câu của mỗi phần đúng `question_type` của phần đó, trong phạm vi chương của phần, đúng phân bố độ khó của mẫu. `chapter` là chương gốc của câu.

Một mục trong `shortages`:

```json
// đề theo chương
{"chapter": "12C4", "difficulty": "TH", "requested": 4, "available": 3,
 "section_order": null, "section_title": null, "question_type": null}
// đề theo mẫu kỳ thi (difficulty null: phần không quy định độ khó)
{"chapter": "12C4", "difficulty": null, "requested": 2, "available": 1,
 "section_order": 3, "section_title": "Phần III. Trả lời ngắn", "question_type": "SHORT_ANSWER"}
```

## Lỗi và trường hợp biên

| Mã | Khi nào |
| --- | --- |
| 401 / 403 | Chưa đăng nhập; tài khoản không phải học sinh (`FORBIDDEN_ROLE`) |
| 404 | Không có phiên; phiên của học sinh khác; phiên chưa có bản xem trước; chưa có đề nháp |
| 409 | `version` lệch (`detail.current_version` là bản mới nhất); xác nhận bản đã `BUILT` |
| 422 `INVALID_STRUCTURE` | Cấu trúc ôn theo chương vi phạm luật (`detail.errors`: chương không có trong danh mục, quá 50 câu, loại hết mức độ khó, chương lặp) |
| 422 `TEMPLATE_CONFLICT` | Chỉnh bản theo mẫu kỳ thi ngoài phần được phép (`detail.errors` nêu lý do: mẫu cố định số câu, độ khó; chương ngoài phạm vi mẫu; chương vượt khối) |
| 422 | Sai kiểu dữ liệu, tin nhắn rỗng |

## Luồng kiểm thử

Test tự động: `cd backend && pytest` (SQLite trong bộ nhớ, ngân hàng, lịch sử và mẫu kỳ thi tự dựng). Theo file:

| File | Kiểm gì |
| --- | --- |
| `tests/test_exam_chat_rules.py` | Luật thuần: chia câu, chỉnh bản xem trước, đọc tin nhắn, nhận diện kỳ thi |
| `tests/test_exam_chat_api.py` | Ôn theo chương qua HTTP: SSE, chỉnh qua chat và API, `version`, dựng đề, các ca hỏi lại và từ chối |
| `tests/test_exam_chat_template.py` | Ôn theo mẫu kỳ thi: một mẫu, nhiều mẫu, thiếu loại kỳ thi, dựng đề theo phần và loại câu, báo thiếu theo phần, chỉnh xung đột bị từ chối (chat và API), thu hẹp chương, chuyển về ôn theo chương, nối với tra cứu #5 |
| `tests/test_exam_chat_ownership.py` | Chủ sở hữu: học sinh khác nhận 404 ở mọi route kể cả SSE, không mạo danh qua `student_ref` |
| `tests/test_exam_chat_integration.py` | Trọn luồng với đăng nhập thật (#8) và tra mẫu thật (#5): 401, 403 với admin, không mạo danh, học sinh khác 404; admin duyệt mẫu rồi học sinh dựng đề theo mẫu; mẫu nháp không lộ; admin sửa mẫu đã duyệt thì lượt chat sau dùng ngay |
| `tests/test_agent_parity.py` | Đối chiếu với `codebase/agent.py` trên 13 câu thử trong `eval/benchmark.csv`, cùng dữ liệu `data/*.csv`: so loại kết quả, từng dòng cấu trúc (chương, số câu, phân bố độ khó) và đúng tập mã câu của đề nháp |

Ca trọn luồng tiêu biểu:

1. HS01 nhắn "Ra đề ôn chương em hay sai" → SSE có `message`, `preview` (12C1, 10 câu, `PROPOSED`), `done`; chưa có mã câu.
2. "giảm còn 4 câu" → `EDITED`, version 2.
3. `PATCH` với version 1 → `409`; với version 2 đổi sang 12C4 chỉ TH → version 3.
4. "Em xác nhận, tạo đề nháp" → dùng bản đã sửa qua API, đề nháp 3 câu 12C4 và `shortages` báo thiếu 1 câu; không có đáp án.
5. "Em muốn ôn thi cuối kỳ 1 lớp 12" → bản xem trước theo mẫu (3 phần). "giảm còn 8 câu" bị từ chối, version giữ nguyên. "xác nhận" → đề nháp theo từng phần, đúng loại câu, báo thiếu ở phần trả lời ngắn.

Chưa kiểm với PostgreSQL thật và dữ liệu nền. Đã kiểm SQL của migration bằng `alembic upgrade 0004:0006_exam_chat --sql` (chuỗi `0004 → 0005_student_auth → 0005_exam_templates → 0006_exam_chat`).

## Phần còn chờ

| Phần | Chờ | Hiện tại | Đổi ở đâu |
| --- | --- | --- | --- |
| Lịch sử làm bài thật | Chưa có bảng kết quả làm bài | `NoHistory`: agent nói chưa có lịch sử và hỏi chương | `get_student_history()` |
| Diễn đạt bằng model thật | Chốt nhà cung cấp và key | Trả văn bản dựng bằng code, chia theo dòng | `get_reply_writer()` |
| Định nghĩa "câu đã duyệt" | #3, #11 | `visibility = 'PUBLISHED'` | `APPROVED_VISIBILITY` trong `question_bank_repository.py` |

Các hàm `get_*` ở trên nằm trong `backend/app/api/deps.py`. Đã nối: đăng nhập (`get_requester` lấy từ `StudentDep`, khoá ngoại `exam_chat_sessions.user_id → users.user_id`) và tra mẫu đã duyệt của #5 (`get_exam_template_source`).

## Tài liệu liên quan

- [Các lớp backend](../architecture/backend-layers.md)
- [API mẫu cấu trúc đề](exam-templates-api.md) (#5)
- [API xác thực](auth-api.md) (#8)
- Mã: `backend/app/api/v1/exam_chat.py`, `backend/app/usecase/exam_chat.py`, `backend/app/usecase/exam_preview_rules.py`, `backend/app/usecase/exam_template_plan.py`, `backend/app/usecase/exam_chat_intent.py`, `backend/app/service/exam_chat_sources.py`
