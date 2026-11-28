# API dashboard học tập

Trang **Tổng quan** và **Hồ sơ** của học sinh đọc số liệu từ endpoint này: điểm qua các lượt, chuỗi ngày học, thống kê theo chương và các lượt làm gần đây. Số liệu tính từ các lượt làm bài đã chấm trong [API làm bài online](online-exam-attempts-api.md). Agent tạo đề cũng dùng cùng cách đếm cho gợi ý "ôn chương mình hay sai".

## Điều kiện gọi

- Gọi HTTP qua `/api/v1` với cookie phiên của học sinh. Admin nhận `403 FORBIDDEN_ROLE`, khách nhận `401`.
- Server chỉ đọc lượt của chính tài khoản đang đăng nhập. Phản hồi có `Cache-Control: no-store`.
- Dùng tối đa 500 lượt đã chấm gần nhất. Lượt đang làm dở không được tính.

## Endpoint và hợp đồng

### `GET /study/dashboard`

Không có tham số. Trả `200` với `DashboardOut`:

| Trường | Ý nghĩa |
| --- | --- |
| `streak.current` | Số ngày liên tiếp có ít nhất một lượt được chấm (nộp tay hoặc hết giờ), tính theo ngày Việt Nam (`Asia/Ho_Chi_Minh`). Hôm nay chưa học thì chuỗi tính tới hôm qua |
| `streak.best` | Chuỗi dài nhất từ trước tới nay |
| `streak.days` | 84 ngày gần nhất, mỗi phần tử `{date, studied}`, cũ trước mới sau, phần tử cuối là hôm nay |
| `totals` | `exams` (số đề khác nhau đã làm), `questions` (tổng câu đã chấm), `minutes` (tổng thời gian làm), `average` (điểm trung bình, `null` khi chưa có lượt) |
| `scores` | Điểm từng lượt theo thứ tự thời gian: `attempt_id`, `draft_id`, `title`, `date`, `score` (thang 10) |
| `chapters` | Thống kê theo **chương cha**: `code`, `name`, `grade` (suy từ mã, vd `12C1` là lớp 12), `correct`, `total`. Sắp theo tỉ lệ đúng tăng dần. Chỉ câu đúng hoàn toàn tính là đúng; câu Đúng/Sai đúng một phần không tính |
| `recent` | Tối đa 5 lượt mới nhất, mới trước. Mỗi phần tử có `attempt` (`attempt_id`, `started_at`, `finished_at`, `duration_seconds`, `score`, `correct`, `total`, `answered`, `reason`) và `exam` (`draft_id`, `title`, `duration_minutes`, `question_count`) |

`title` lấy từ bản đề đã cố định khi bắt đầu lượt, nên vẫn đúng khi đề nháp bị đổi sau đó. Thời gian làm là tổng thời gian từng câu; lượt thiếu số liệu này dùng khoảng từ lúc bắt đầu tới lúc nộp, và không vượt thời lượng đề.

Ví dụ rút gọn cho tài khoản chưa có lượt nào:

```json
{
  "streak": {"current": 0, "best": 0, "days": [{"date": "2026-09-06T00:00:00+07:00", "studied": false}]},
  "totals": {"exams": 0, "questions": 0, "minutes": 0, "average": null},
  "scores": [], "chapters": [], "recent": []
}
```

Frontend đổi `attempt_id` thành `online-<id>` và `draft_id` thành `draft-<id>` để khớp đường dẫn `/results/online-15` và `/exams/draft-42`.

## Lỗi và trường hợp biên

| Mã | Điều kiện |
| --- | --- |
| `401 SESSION_MISSING` và các mã `SESSION_*` | Chưa đăng nhập hoặc phiên không còn dùng được |
| `403 FORBIDDEN_ROLE` | Tài khoản không phải học sinh |

Tài khoản chưa có lượt nào là trường hợp bình thường và trả phản hồi rỗng như ví dụ trên. Hai lượt kết thúc quanh nửa đêm giờ Việt Nam được xếp vào ngày theo giờ Việt Nam, không theo UTC.

## Luồng kiểm thử

```powershell
cd backend; pytest -q tests/test_study_dashboard.py
```

Bộ kiểm thử phủ: tài khoản rỗng, một lượt, ranh giới nửa đêm giờ Việt Nam, chuỗi hiện tại và tốt nhất, chỉ tính lượt đã chấm, câu Đúng/Sai đúng một phần, và cô lập giữa các học sinh.

Kiểm tay: đăng nhập học sinh mới, `GET /api/v1/study/dashboard` trả phản hồi rỗng. Làm và nộp một đề, gọi lại: `streak.current` là 1, `recent` có một lượt, `chapters` có các chương của đề.

## Tài liệu liên quan

- [API làm bài online](online-exam-attempts-api.md)
- [Trang học sinh frontend](../architecture/frontend-student-pages.md)
- Mã: `backend/app/usecase/study_stats.py`, `backend/app/usecase/study_dashboard.py`, `backend/app/api/v1/study_dashboard.py`
