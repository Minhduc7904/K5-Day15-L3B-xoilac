# API làm bài online

Các màn hình **Đề của tôi**, **Làm bài** và **Kết quả** dùng API này cho đề do agent dựng. Server lưu đáp án, thời hạn và kết quả luyện tập theo tài khoản.

## Điều kiện gọi

- Gọi HTTP qua `/api/v1` với cookie phiên học sinh. Server trả `404` khi ID đề hoặc ID lượt thuộc tài khoản khác.
- Kết nối Socket.IO bằng vé dùng một lần theo [API realtime](realtime-api.md). UI bật luồng này với `NEXT_PUBLIC_MOCK_MODE=false` và `NEXT_PUBLIC_EXAM_CHAT_LIVE=true`.
- ID giao diện `draft-42` và `online-15` tương ứng với `draft_id=42` và `attempt_id=15` ở backend.

## Endpoint và hợp đồng

| Method | Path sau `/api/v1` | Hành vi |
| --- | --- | --- |
| GET | `/study/attempts` | Tóm tắt theo ID đề gồm `active`, `count`, `best_score`, `last_at`. |
| GET | `/study/exams/{draft_id}/attempts` | Trả `latest` và `history` lượt đã chấm, mới nhất trước. |
| POST | `/study/exams/{draft_id}/attempts` | Body `{"restart": false}`. Trả lượt đang làm hoặc kết quả gần nhất. Nếu chưa từng làm, tạo lượt mới. `restart: true` tạo lượt sau khi lượt trước đã kết thúc. |
| GET | `/study/attempts/{attempt_id}` | Trả trạng thái hiện hành, bản đề đã cố định và `server_now`. Khi đã quá hạn, yêu cầu này cũng có thể hoàn tất chấm. |
| PATCH | `/study/attempts/{attempt_id}` | Lưu một thay đổi đáp án hoặc một đoạn thời gian. Trả trạng thái mới sau khi commit. |
| POST | `/study/attempts/{attempt_id}/submit` | Nộp và chấm. Yêu cầu gửi lại trả cùng lượt và điểm. |
| GET | `/study/attempts/{attempt_id}/result` | Trả kết quả từng câu, khóa chấm và lời giải sau khi lượt đã chấm. |
| GET | `/study/attempts/{attempt_id}/media/{media_id}` | Tải ảnh trong đề hoặc ảnh lời giải sau khi chấm. |

Trạng thái lượt gồm `status` (`in_progress` hoặc `graded`), `started_at`, `deadline_at`, `finished_at`, `reason` (`manual` hoặc `timeout`), `revision`, `answers`, `current` và `question_seconds`. Thời gian là ISO 8601. `deadline_at: null` là đề vô hạn. Mỗi phần tử của `answers` có `value` và `revision` riêng.

### Lưu đáp án và thời gian

Ví dụ lưu lựa chọn A. `base_revision: 0` dùng cho câu chưa được lưu.

```json
{
  "mutation_id": "11111111-1111-4111-8111-111111111111",
  "question": "Q00801",
  "base_revision": 0,
  "answer": "A"
}
```

Câu Đúng/Sai dùng mảng bốn phần tử `true`, `false` hoặc `null` theo thứ tự mệnh đề của bản đề. TLN dùng chuỗi. Gửi `answer: null` để xóa đáp án. Gửi lại cùng `mutation_id` để thử lại thao tác cũ.

Để lưu thời gian kể cả khi chưa trả lời, gửi `mutation_id`, `question`, `tab_id` (UUID), `elapsed_ms` (0–6000), và vị trí hiện tại `current`. Khi ngừng đo, gửi thêm `release_tab: true`. Server giữ quyền đo cho một tab tại một thời điểm. Giao diện gửi đoạn thời gian khi đổi câu, ẩn tab, rời trang hay nộp, và checkpoint mỗi 4 giây khi đang hoạt động. Thời gian quan sát có thể thiếu đoạn cuối nếu trình duyệt tắt đột ngột khi mất mạng.

### Room Socket.IO

| Sự kiện | Dữ liệu và phản hồi |
| --- | --- |
| `attempt:join` | Client gửi `{attempt_id}`. Server xác minh chủ sở hữu, tham gia room `attempt:<id>` và ACK `{ok: true, state}`. |
| `attempt:save` | Client gửi `{attempt_id, update}`, trong đó `update` cùng dạng body PATCH. Trả ACK sau khi ghi DB. |
| `attempt:updated` | Server gửi `{attempt_id, revision, reason: null}` khi có phiên bản mới. Các tab lấy bản mới qua GET. |
| `attempt:finished` | Server gửi `{attempt_id, revision, reason}` sau khi đã chấm. Client có thể lấy lại kết quả nếu bỏ lỡ sự kiện. |
| `attempt:leave` | Client gửi `{attempt_id}` khi rời màn hình làm bài. |

Tiến trình API theo dõi các phiên bản đã commit của lượt có tab tham gia room. Nhờ vậy, thay đổi từ HTTP hoặc worker riêng đều được báo vào Socket.IO. Khi kết nối lại, client vào room rồi đọc bản hiện hành trước khi gửi dữ liệu đang chờ.

## Lỗi và trường hợp biên

| Mã lỗi | Điều kiện |
| --- | --- |
| `404 EXAM_NOT_FOUND`, `ATTEMPT_NOT_FOUND` | ID không tồn tại hoặc nằm ngoài quyền của tài khoản. |
| `409 ANSWER_CONFLICT` | Tab khác đã lưu câu này. Đọc lại phiên bản và cho học sinh chọn đáp án muốn giữ. |
| `409 ATTEMPT_FINISHED` | Lượt đã nộp hoặc đã tới hạn. Các đáp án mới bị từ chối. |
| `409 NOT_GRADED` | Lượt chưa nộp và chưa tới hạn. |
| `422 INVALID_EXAM`, `MISSING_GRADING_KEY` | Đề chưa đủ dữ liệu để chấm. Lượt mới chưa được tạo. |

Theo giờ server, cập nhật từ thời điểm `now >= deadline_at` bị từ chối. Worker tự hoàn tất lượt đến hạn trong tác vụ `exam-expiry`, kể cả khi không có tab nào mở. Đề vô hạn kết thúc sau khi học sinh nộp.

## Luồng kiểm thử

1. Tạo một đề, bắt đầu, lưu một câu và thoát trang. Đăng nhập cùng tài khoản ở trình duyệt khác rồi mở **Làm tiếp**. Đáp án đã lưu phải xuất hiện.
2. Với một đề có thời lượng, đóng mọi tab rồi chờ tới hạn trong khi worker đang chạy. Mở lại đề và kiểm tra thông báo hết giờ cùng trang kết quả.
3. Mở hai tab cùng một lượt, gửi hai đáp án có cùng phiên bản câu. Lần lưu thứ hai phải báo `ANSWER_CONFLICT`. Thử vào room bằng tài khoản khác phải bị từ chối.

## Tài liệu liên quan

- [Kế hoạch làm bài online](../architecture/online-exam-attempts.md)
- [Chạy worker học sinh](../operations/run-local-stack.md#chạy-worker-học-sinh)
- [API học sinh tạo đề ôn](user-exam-api.md)
