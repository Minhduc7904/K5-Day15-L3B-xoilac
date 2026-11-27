# Canvas — xoilac · Track F

> Điền ở guide bước 1.4. CP1 17:00 Thứ Sáu 27/11: nộp bản đầu, đủ 7 dòng (dòng 4 được ghi giả thuyết + nguồn sẽ kiểm).
> CP2 19:30 Thứ Sáu 27/11: cập nhật (số bằng chứng đầu, lát cắt đã chốt) và điền dòng "Đã đổi gì so với CP1".
> Track F: chép thêm thẻ đề của nhóm (khung trong file track F) xuống dưới bảng này.

| # | Dòng | Nhóm điền |
|---|---|---|
| 1 | Track + lát cắt dự kiến | Track F — Học sinh lớp 10–12 tự ôn Toán có thể khó chọn phần ôn tiếp sau khi chữa đề. Lát cắt dự kiến: đề ôn ngắn theo chương yếu. |
| 2 | Người dùng chính (một vai cụ thể — không phải "học viên nói chung") | Học sinh THPT (lớp 10, 11, 12) tự ôn môn Toán cho kiểm tra, thi học kỳ hoặc thi tốt nghiệp, đã làm ít nhất một đề |
| 3 | Pain một câu: ai — đang làm gì — vướng đâu — hậu quả | Học sinh THPT — làm đề Toán để ôn tập và ôn thi — chỉ có tổng điểm, không biết mình yếu chương nào nên chọn đề ôn không trúng chỗ yếu — ôn dàn trải, tốn giờ ở chương đã vững, điểm khó tăng *(giả thuyết, chưa kiểm)* |
| 4 | Bằng chứng đầu — CP1: giả thuyết + nguồn sẽ kiểm · CP2: số đầu tiên + 1 trích dẫn | CP1 — giả thuyết: ≥2/3 học sinh trong mẫu khảo sát báo ít nhất một lần trong 30 ngày qua chữa đề Toán xong mà chưa biết ôn phần nào tiếp. Nguồn chính dự kiến: Google Form với ≥20 học sinh lớp 10–12 phù hợp ở trung tâm dạy thêm. Chưa có kết quả. Chi tiết: `evidence/hypothesis.md`. |
| 5 | **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả) | Học sinh THPT nhắn yêu cầu ôn phần hay sai để agent dựa trên lịch sử làm bài và đề xuất cấu trúc đề ôn cho học sinh xem trước, rồi dựng đề ngắn từ các câu đã duyệt. |
| 6 | AI tự làm đến đâu + 1 dòng lý do: sai thì ai chịu gì | AI gợi ý, người quyết: agent nói rõ trong chat vì sao chọn chương đó và đề xuất đề ôn, học sinh chỉnh bằng lời (đổi chương, số câu, độ khó) trước khi làm. Sai thì học sinh mất thời gian ôn chưa đúng chỗ (rẻ, sửa được). Câu hỏi chỉ lấy từ ngân hàng đã duyệt, agent không tự bịa câu hỏi hay đáp án |
| 7 | Phân công có tên | Nguyễn Minh Đức — đội trưởng, PO, Tech Lead, DevOps, đảm bảo chất lượng sản phẩm và chốt quyết định chính · Đỗ Thị Thu Hằng — backend và frontend · Phùng Văn Thanh Cao và Vũ Quang Huy — AI Agent. |
| — | *(CP2)* Đã đổi gì so với CP1 | (1) Thêm bước học sinh **xem trước cấu trúc đề** và chỉnh bằng lời trước khi agent dựng đề. (2) Làm rõ "tự tạo đề" là **ghép câu đã duyệt từ ngân hàng**, agent không tự viết câu hay đáp án. (3) Kiến trúc có thêm nhánh ôn **theo kỳ thi có cấu trúc sẵn** và luồng **admin nhập PDF** (tách câu, so embedding để gợi ý chương và độ khó, admin duyệt); hai phần này **chưa nằm trong lát cắt đo**, lát cắt đo vẫn là luồng cá nhân hóa. (4) Có dữ liệu thật: ngân hàng 14.146 câu Toán của trung tâm (repo chỉ chứa mẫu 1.279 câu, không kèm dữ liệu học sinh), thay cho ngân hàng tự dựng ở CP1. (5) Chưa có số bằng chứng pain: khảo sát chưa chạy, dòng 4 giữ nguyên giả thuyết. Chi tiết: `spec.md` §4. |

# Track F · Examind — Nền tảng AI Agent hỗ trợ tạo đề thi và cá nhân hóa ôn tập môn Toán THPT

*Tên đang dùng trong repo: Examind (Exam + Mind, đánh giá thông minh). Slogan trong repo: "Beyond traditional assessment".*

> Mục đánh dấu *(dự kiến)* là kế hoạch của nhóm, chưa phải kết quả đã kiểm. Chưa có số liệu thật nào ở thẻ này.

**Lĩnh vực.** Giáo dục phổ thông, ôn tập và ôn thi môn Toán ở THPT (lớp 10, 11, 12). Không thuộc khoá AI20K nên không thuộc track A.
**Pain.** Học sinh THPT — làm đề Toán để ôn tập và ôn thi — chỉ có tổng điểm, không biết mình yếu chương nào nên chọn đề ôn không trúng chỗ yếu — ôn dàn trải, tốn giờ ở chương đã vững, điểm khó tăng *(giả thuyết, chưa kiểm)*.
**Insight từ người dùng thật.** Chưa có kết quả. Nhóm dự kiến dùng Google Form để kiểm giả thuyết với ≥20 học sinh THPT phù hợp ngoài nhóm. Xem `evidence/hypothesis.md`.
**Người dùng.** Học sinh lớp 10–12 tự ôn Toán và đã làm ít nhất một đề. Nhóm dự kiến tiếp cận các bạn tại trung tâm dạy thêm nơi Nguyễn Minh Đức đang làm quản lý.
**Data.** Ngân hàng câu hỏi là dữ liệu thật của trung tâm dạy thêm do một thành viên nhóm quản lý: 14.146 câu Toán lớp 10–12; repo chỉ chứa mẫu 1.279 câu dùng được (đủ chương, độ khó, đáp án, không hình) trong `data/question_bank.csv`, bản đầy đủ để ở máy nhóm. Repo không chứa dữ liệu học sinh thật; kết quả làm bài của học sinh mẫu HS01–HS04 là tự dựng có seed (`data/student_results.csv`). Nguồn, cách xử lý và giới hạn trong `data/DATA_CARD.md`.
**Lát cắt.** Học sinh THPT nhắn yêu cầu ôn phần hay sai để agent dựa trên lịch sử làm bài và đề xuất một đề ngắn từ các câu đã duyệt.
**Công cụ của agent** *(hợp đồng dự kiến cho `codebase/tools.py`; repo hiện còn dùng công cụ mẫu)*.
- `get_student_results(student_id)` · input: mã học sinh · output: số câu đúng/sai theo chương · không tác động ra ngoài.
- `search_question_bank(chapter, difficulty, n)` · input: mã chương, độ khó (NB/TH/VD/VDC), số câu · output: danh sách câu hỏi kèm mã câu · không tác động ra ngoài.
- `build_exam_draft(structure, question_ids)` · input: cấu trúc đã xác nhận, mã câu · output: bản nháp đề · chỉ tạo bản nháp, học sinh duyệt trước khi làm.
- `get_exam_template(exam_code)` *(nhánh kỳ thi, chưa trong lát cắt)* · input: mã kỳ thi · output: cấu trúc đã xác thực hoặc "chưa có" · không tác động ra ngoài.
**Bộ câu thử.** Câu thường: "ra đề ôn chương mà em hay sai". Câu khó: học sinh chưa làm đề nào, kết quả mâu thuẫn, yêu cầu chương mà ngân hàng không có câu. Câu phải từ chối: xin đáp án để chép, đòi sửa điểm, "bỏ qua hướng dẫn trước đó", hỏi ngoài môn Toán. Đạt khi câu được chọn đúng chương yếu và có trong ngân hàng, ngưỡng chốt ở CP2.
**Persona chi phí.** Ít (ôn rải rác) · vừa (mỗi tuần một đề ôn) · nhiều (ôn dồn trước kỳ thi). Tần suất sẽ được đối chiếu khi có dữ liệu người dùng.
**Bẫy.**
- Không gặp được học sinh THPT thật nên không có insight, chỉ có ý tưởng.
- Lát cắt phình ra khi tích hợp nhiều phiên bản ma trận, luồng PDF/OCR hoặc toàn bộ chức năng làm đề online.
- Agent tự bịa câu hỏi hoặc đáp án sai kiến thức Toán, hoặc chọn câu không thuộc chương yếu mà vẫn nói là đúng.
**An toàn.**
- Agent không tự sinh câu hỏi hay đáp án; chỉ chọn câu từ ngân hàng đã duyệt, không có thì nói không có.
- Không dùng điểm hay dữ liệu thật của học sinh; không xếp hạng, so sánh học sinh với nhau.
- Chỉ đề xuất đề ôn, không ghi điểm chính thức. Không xin thông tin cá nhân.

**Hướng mở rộng.** Đề ôn thích ứng với cả phần học sinh cần luyện và cấu trúc của từng kỳ thi/năm, luồng admin nhập PDF để mở rộng ngân hàng, xuất đề ra bản in giấy, và (sau đó) làm đề online với chấm bằng code và thống kê; các phần này chưa đo ở CP2. Lát cắt đang đo ở CP2 tập trung vào đề ôn ngắn theo chương yếu, có bước xem trước cấu trúc.
