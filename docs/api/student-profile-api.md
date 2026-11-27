# API hồ sơ học sinh và credit

## Điều kiện gọi

Các endpoint dưới `/api/v1/student/me` dùng phiên đăng nhập hiện tại, yêu cầu vai trò `student` và tự lấy mã người dùng từ phiên.

## Hồ sơ

`GET /api/v1/student/me/profile` trả `{ "completed": false, "profile": null, "email_verified": true }` khi học sinh chưa điền hồ sơ. Hồ sơ đã lưu có `completed: true`. Trường `profile` có dữ liệu học tập, `display_name`, `email`, `email_verified` và `joined_at`.

`PUT /api/v1/student/me/profile` tạo hoặc thay thế thông tin học tập và trả bản đã lưu. Tên hiển thị nếu được gửi sẽ cập nhật tài khoản. Khi bỏ trường này, tên hiện tại được giữ lại.

```json
{
  "school_name": "THPT Mẫu",
  "grade": 12,
  "target_score": 9,
  "exam_period": "national_high_school",
  "study_days": [1, 3, 6],
  "reminder_time": "08:00"
}
```

- `grade` nhận 10–12. `target_score` nhận 7, 8 hoặc 9.
- `exam_period` nhận `midterm_1`, `final_1`, `midterm_2`, `final_2` hoặc `national_high_school`.
- `study_days` nhận từ một đến sáu giá trị khác nhau, từ 1 (T2) đến 6 (T7).
- `reminder_time` là giờ Việt Nam theo phút, hoặc `null` để tắt. Khi nhập giờ, backend yêu cầu email đã xác minh.

## Credit

`GET /api/v1/student/me/credits?limit=20` trả `balance`, `limit` (trần số dư 500), `daily_grant` (mức cộng tối đa 100), `history` và `next_before_id`. Mỗi giao dịch có `id`, `delta`, `balance_after`, `reason`, `effective_on` (ngày Việt Nam) và `created_at` (thời điểm ghi).

Lịch sử mặc định 20 giao dịch mỗi trang, tối đa 50. Nếu `next_before_id` khác `null`, truyền giá trị này ở tham số `before_id` cho trang kế tiếp. Học sinh mới nhận giao dịch `initial_grant` bằng 500 credit. Job hằng ngày ghi `daily_grant` bằng số credit thực cộng. Khi bật chat tạo đề thật, `exam_creation` ghi khoản trừ 100 credit cho lần lưu đề đầu tiên của một phiên. Các lần chỉnh trong cùng phiên không tạo giao dịch mới.

## Lỗi và luồng kiểm thử

- Khách gọi nhận 401, vai trò admin nhận 403.
- Giá trị ngoài tập hợp hợp lệ hoặc giờ nhắc sai định dạng nhận 422. Email chưa xác minh khi bật nhắc nhận 422 `REMINDER_EMAIL_UNVERIFIED`.
- Với một học sinh vừa xác minh OTP, đọc trạng thái chưa hoàn tất, lưu mẫu bên trên rồi đọc lại. Credit trả một giao dịch `+500`. Lưu với `reminder_time: null` tắt email.

## Tài liệu liên quan

- [Trang học sinh frontend](../architecture/frontend-student-pages.md)
- [Chạy bộ khung local](../operations/run-local-stack.md)
