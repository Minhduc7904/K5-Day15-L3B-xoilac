# API thống kê cho admin

Trang **Tổng quan** của admin đọc số liệu phân tích từ năm endpoint dưới `/api/v1/admin/stats`. Ngoài ra `GET /admin/stats/online-students` (#20) đếm học sinh đang online, xem [API realtime](realtime-api.md).

## Điều kiện gọi

- Gọi HTTP qua `/api/v1` với cookie phiên admin (header `X-Auth-Scope: admin`) hoặc `Authorization: Bearer`. Học sinh nhận `403 FORBIDDEN_ROLE`, khách nhận `401`.
- Mọi endpoint chỉ đọc và chỉ trả **số tổng hợp**: không có email, tên hay nội dung bài làm của từng học sinh.
- Tham số `range` nhận `7`, `30` hoặc `90` (mặc định `30`); giá trị khác trả `422`. Đó là số ngày gần nhất tính tới hôm nay, ngày theo giờ Việt Nam (`Asia/Ho_Chi_Minh`).
- Chưa có cache phía server; mỗi lần gọi tính lại từ cơ sở dữ liệu. Phép nhóm theo ngày làm bằng Python trên các dòng đã chặn theo mốc thời gian; nếu dữ liệu lớn lên, chuyển sang bảng tổng hợp theo ngày.
- Định nghĩa dùng chung: **học sinh hoạt động** trong một ngày là học sinh có phiên đăng nhập mới hoặc bắt đầu một bài làm ngày đó. **Bài hoàn thành** là bài ở trạng thái `graded`.

## `GET /admin/stats/overview?range=30`

Sáu chỉ số đầu trang và số việc cần chú ý.

| Trường | Ý nghĩa |
| --- | --- |
| `kpis[]` | `{key, value, previous, series}`. `previous` là cùng chỉ số ở kỳ liền trước dài bằng nhau, `null` khi không so sánh được. `series` là chuỗi theo ngày của kỳ này (chỉ có ở ba chỉ số đếm) |
| `kpis[].key` | `active_students`, `new_students`, `completed_attempts`, `average_score` (thang 10), `published_questions`, `import_success_rate` (0..1, bỏ qua lượt đang xử lý) |
| `attention` | `pending_pdf_drafts` (câu từ PDF chờ duyệt, toàn bộ), `draft_questions` (câu nháp chưa lưu trữ), `failed_imports` (lượt nhập PDF lỗi trong kỳ) |
| `generated_at` | Thời điểm tính, UTC, kết thúc bằng `Z` |

## `GET /admin/stats/growth?range=30`

| Trường | Ý nghĩa |
| --- | --- |
| `days`, `signups`, `dau`, `wau` | Ba chuỗi cùng độ dài `range`, cũ trước mới sau: học sinh đăng ký mới, học sinh hoạt động trong ngày, và trong 7 ngày kết thúc ở ngày đó |
| `active_students`, `stickiness` | Số học sinh hoạt động ít nhất một lần trong kỳ; `stickiness` = DAU trung bình chia số đó (`null` khi chưa ai hoạt động) |
| `funnel[]` | Phễu **lồng nhau** của học sinh đăng ký trong kỳ: `registered` → `verified` (xác minh email) → `profile` (hoàn tất hồ sơ) → `drafted` (có đề nháp) → `attempted` (có bài làm). Mỗi bước chỉ đếm người đã qua bước trước |
| `heatmap` | Ma trận 7 × 24: hàng là thứ (0 = thứ Hai), cột là giờ trong ngày, giá trị là số bài làm bắt đầu |
| `grades`, `targets` | Số học sinh theo khối (10, 11, 12) và điểm mục tiêu (7, 8, 9). Tính toàn bộ hồ sơ, không theo `range` |

## `GET /admin/stats/learning?range=30`

Chỉ tính bài bắt đầu trong kỳ.

| Trường | Ý nghĩa |
| --- | --- |
| `graded`, `median`, `average` | Số bài đã chấm, điểm trung vị và trung bình (`null` khi chưa có bài) |
| `bins[]` | 10 khoảng điểm `0–1` … `9–10`; điểm 10 tính vào khoảng cuối |
| `weekly[]` | Theo tuần (thứ Hai là đầu tuần, `week` là ngày đó): `attempts`, `average` |
| `outcomes[]` | Theo tuần: `manual` (học sinh nộp), `timeout` (hết giờ), `in_progress` (chưa chấm) |
| `chapters[]` | Tối đa 10 **chương gốc** có tỉ lệ đúng thấp nhất: `code`, `name`, `correct`, `total`, `rate`. Chỉ câu đúng hoàn toàn tính là đúng. Chương có dưới `min_answers` (5) câu làm bị ẩn và đếm trong `chapters_hidden` |

Dùng tối đa 5000 lượt gần nhất trong kỳ.

## `GET /admin/stats/bank?range=30`

| Trường | Ý nghĩa |
| --- | --- |
| `published`, `draft`, `private`, `archived` | Số câu theo trạng thái. Câu đã lưu trữ chỉ tính vào `archived` |
| `by_type`, `by_grade`, `by_difficulty` | Chỉ câu đã đăng. `by_difficulty` luôn đủ `NB`, `TH`, `VD`, `VDC` |
| `coverage[]` | Mỗi chương gốc: `code`, `name`, `grade`, `counts` (câu đã đăng theo `NB/TH/VD/VDC`), `total`. Chương gốc chưa có câu nào vẫn có mặt với toàn số 0 |
| `shortages` | Từ `exam_drafts.shortages` của các đề nháp tạo trong kỳ: `drafts`, `drafts_with_shortage`, và `chapters[]` (`code`, `name`, `missing` = tổng số câu yêu cầu mà không có, `occurrences`) cộng dồn theo chương gốc, tối đa 10, nhiều thiếu nhất trước |

## `GET /admin/stats/operations?range=30`

| Trường | Ý nghĩa |
| --- | --- |
| `days` | Trục ngày chung cho `imports` và `credits` |
| `imports` | Lượt nhập PDF tạo trong kỳ: `total`, `success_rate`, `by_status[]`, `failed_by_stage[]`, và ba chuỗi theo ngày `completed`, `failed`, `in_flight` (`queued`/`processing`) |
| `pdf_drafts` | Số bản nháp PDF theo trạng thái (`pending`, `approved`, `rejected`), toàn bộ |
| `credits` | `granted` và `spent` theo ngày (số credit cộng và trừ, `spent` là số dương) |
| `chat` | Phiên chat tạo đề mở trong kỳ: `sessions`, `with_draft`, `with_attempt` (có ít nhất một bài làm từ đề của phiên), `daily` |

## Kiểm thử

`backend/tests/test_admin_analytics.py` kiểm quyền (401/403), `range` hợp lệ, cơ sở dữ liệu rỗng không lỗi, từng endpoint với dữ liệu tự dựng, và các hàm thuần (khoảng điểm, chương gốc, thiếu câu, tỉ lệ nhập PDF thành công, hoạt động 7 ngày).

```powershell
python -m pytest backend/tests/test_admin_analytics.py
```
