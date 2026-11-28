# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử | Claude Code | Viết phần gọi model thật trong `codebase/ai.py` (OpenAI, Claude, Gemini, Ollama), đọc token từ `usage`. | Thử bằng máy chủ giả, rồi `python run.py eval --try` với gpt-5.4-mini: token vào/ra lớn hơn 0. | Nguyễn Minh Đức |
| Viết câu thử (benchmark) | Claude Code | Soạn B24–B27 (`tu_viet`) và dựng B19–B23 từ số liệu ngân hàng thật; B14–B18 chép nguyên văn từ khảo sát câu 9. | Mỗi câu thử có `source`; câu thử AI viết được ghi rõ là `tu_viet`; `run.py check` pass. | Nguyễn Minh Đức |
| Chấm cột `pass` bằng LLM (nếu có) | Không dùng | Cột `pass` do người chấm, không có LLM chấm. | Đức chấm lượt 1 và 2; Hằng chấm độc lập 5 câu của lượt 2, khớp 3/5 (`eval/second-grader-sheet.md`). | Nguyễn Minh Đức |
| Slide, văn bản | Claude Code | Soạn bản đầu `eval/report.md`, `cost/cost-estimate.md`, `spec.md` §0, §2, §3, §8, `slides/demo-slides.html` (xuất `demo-slides.pdf`), `evidence/summary.md`. | Đức đọc, đối chiếu số với file nguồn và duyệt trước khi commit; số không có nguồn ghi *(tự ước tính)*. | Nguyễn Minh Đức |
| Cấu hình production (#13) | Codex | Rà cấu hình backend, thêm ánh xạ khóa AI trong Compose, cập nhật runbook EC2 và kiểm thử local. | Huy duyệt kế hoạch và phối hợp xác minh trên EC2. | Vũ Quang Huy |
| Cá nhân hóa đề ôn (#41) | Codex | Đọc luồng #40, triển khai thống kê từ lượt đã chấm, nối đề xuất AI với bản xem trước và viết ca kiểm thử. | Huy duyệt phạm vi và ngưỡng thống kê. Đối chiếu số liệu và bản xem trước khi duyệt PR. | Vũ Quang Huy |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
