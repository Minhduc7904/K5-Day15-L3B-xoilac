# Reflection — Nguyễn Minh Đức

> Làm ở guide bước 5.3. Mỗi người một file: chép file này thành `reflection/<ten-khong-dau>.md` (viết thường, không dấu). Hạn: **23:59 Thứ Bảy 28/11**. Mỗi câu 3–6 dòng.

1. Vai trò + phần mình làm (trỏ tới file / commit):
   Đội trưởng, PO, Tech Lead, DevOps. Mình chốt phạm vi và chuẩn "đạt" (`spec.md` §7), thu và xác nhận 23 phiếu khảo sát (`evidence/summary.md`, `evidence/survey/results.csv`), mở rộng bộ câu thử lên 27 câu (`eval/benchmark.csv`, B14–B27), chạy và chấm lượt 1, lượt 2 (`eval/run-1.csv`, `eval/run-2.csv`, `eval/report.md`), điền bảng impact (`spec.md` §2), mô phỏng chi phí (`cost/`, `simulate-1`), làm slide (`demo-slides.pdf`). Phía sản phẩm mình làm seed mẫu ma trận đề (commit 48dd3d4) và duyệt mẫu đề cho chat học sinh (94ad93e).

2. AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):
   Mình dùng Claude Code cho: nối model thật trong `codebase/ai.py`, soạn thêm 14 câu thử, chạy `run.py eval` và `simulate`, soạn bản nháp bảng impact, `eval/report.md`, `cost/cost-estimate.md` và slide. Mình đọc và duyệt trước khi commit. Chỗ phải sửa: lần đầu AI ghi tiếng Việt hỏng khi sửa `ai.py` bằng lệnh shell nên phải khôi phục file và làm lại; số người dùng cho chi phí AI chỉ có thể ghi là *(tự ước tính)* vì nhóm chưa có số học sinh thật, mình giữ đúng nhãn đó; AI không được tự sao chép khóa API, mình tự đưa đường dẫn `.env`. Phần chấm cột `pass` do mình xác nhận, không để AI tự chấm thay.

3. Một câu thử trượt của nhóm và mình học được gì từ nó:
   B25–B27 (so sánh học sinh, tự soạn câu hỏi, giải bài) trượt ở lượt 1: agent chỉ hỏi lại "ôn chương nào" nên học sinh không biết sản phẩm không làm việc đó, và `tu_choi` chỉ đạt 4/7. Mình học được rằng bộ chặn chỉ viết cho các kiểu tấn công đã nghĩ tới sẽ bỏ sót yêu cầu ngoài phạm vi trong `spec.md` §3. Sau khi thêm ba mẫu, lượt 2 đạt 7/7, nhưng mình ghi rõ trong báo cáo là các mẫu được viết sau khi thấy câu trượt nên 3/3 chưa chứng minh được tổng quát; cần bộ câu giữ riêng và người chấm thứ hai.
