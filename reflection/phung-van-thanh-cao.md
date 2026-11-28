# Reflection — Phùng Văn Thanh Cao

> Làm ở guide bước 5.3. Mỗi người một file: chép file này thành `reflection/<ten-khong-dau>.md` (viết thường, không dấu). Hạn: **23:59 Thứ Bảy 28/11**. Mỗi câu 3–6 dòng.

1. Vai trò + phần mình làm (trỏ tới file / commit):
   AI Agent cùng Huy. Theo lịch sử commit: API quản lý và tra cứu mẫu cấu trúc đề thi (#5, commit 6b369bb), chat tạo đề ôn qua SSE, bản xem trước và đề nháp từ câu đã duyệt (#4, commit 49e3da0), ôn theo mẫu kỳ thi và kiểm chủ sở hữu phiên (3a6242c, có test đối chiếu với `codebase/agent.py`), PR #31 và #32.

2. AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):
   Mình dùng Claude để check code backend cho #5 và #4: model, repository, usecase, API, schema, migration, test và tài liệu API (`docs/api/exam-templates-api.md`, `docs/api/user-exam-api.md`).
   Có ba chỗ mình phải sửa hoặc kiểm lại output của Claude. Thứ nhất, mã migration Claude đặt bị trùng với nhánh auth, mình phải đổi thành `0005_exam_templates` và `0006_exam_chat` (bd11b14, 8407d66) rồi nối lại thứ tự sau khi gộp main. Thứ hai là phân quyền: thêm quyền admin cho API mẫu đề và kiểm chủ sở hữu phiên chat (`test_exam_chat_ownership.py`). Thứ ba, luồng chat backend có thể lệch khỏi `codebase/agent.py`, nên mình thêm `test_agent_parity.py` để đối chiếu hai bên thay vì tin luôn output.

3. Một câu thử trượt của nhóm và mình học được gì từ nó:
   Câu B17 ("không biết đề nào sát với cấu trúc thi ở trường") trượt ở cả lượt 1 và lượt 2. Agent chỉ hỏi chung "ôn chương nào", không nói rằng nhóm chưa có cấu trúc đề thi của trường đã xác thực nguồn.
   Nguyên nhân: mẫu `EXAM` trong `codebase/agent.py` chỉ bắt các cụm như "kỳ thi" hay "cấu trúc đề", còn câu này viết "cấu trúc thi ở trường", nên không vào được nhánh kỳ thi, tức nhánh gọi `get_exam_template` và báo thiếu cấu trúc. Phần backend mẫu đề mình làm (#5) có sẵn rồi nhưng không được dùng tới vì bước nhận diện ý định bỏ lỡ.
   Bài học: dữ liệu và công cụ có đủ chưa chắc agent đã dùng đúng. Khâu nhận diện ý định bằng mẫu chữ dễ trượt khi người dùng diễn đạt khác, nên cần thử thêm nhiều cách nói cho cùng một ý định, và khi thiếu nguồn thì phải nói rõ trước khi gợi ý hướng khác. [Báo cáo đánh giá](../eval/report.md)
