# Canvas — xoilac · Track F

> Điền ở guide bước 1.4. CP1 17:00 Thứ Sáu 27/11: nộp bản đầu, đủ 7 dòng (dòng 4 được ghi giả thuyết + nguồn sẽ kiểm).
> CP2 19:30 Thứ Sáu 27/11: cập nhật (số bằng chứng đầu, lát cắt đã chốt) và điền dòng "Đã đổi gì so với CP1".
> Track F: chép thêm thẻ đề của nhóm (khung trong file track F) xuống dưới bảng này.

| # | Dòng | Nhóm điền |
|---|---|---|
| 1 | Track + lát cắt dự kiến | Track F (làn khác, lĩnh vực giáo dục) — đề tài nhóm tự mở: Examind, nền tảng AI Agent hỗ trợ tạo đề thi và cá nhân hóa ôn tập môn Toán THPT. Lát cắt hackathon: app ôn thi Toán THPT, học sinh làm đề online rồi chat với agent để được ra đề ôn vá chương yếu, lấy câu từ ngân hàng câu hỏi theo cấu trúc đề thi các năm |
| 2 | Người dùng chính (một vai cụ thể — không phải "học viên nói chung") | Học sinh lớp 12 đang ôn thi tốt nghiệp THPT môn Toán, đã làm ít nhất một đề thử |
| 3 | Pain một câu: ai — đang làm gì — vướng đâu — hậu quả | Học sinh lớp 12 — làm đề thử Toán để ôn thi — chỉ có tổng điểm, không biết mình yếu chương nào nên chọn đề ôn không trúng chỗ yếu — ôn dàn trải, tốn giờ ở chương đã vững, điểm khó tăng *(giả thuyết, chưa kiểm)* |
| 4 | Bằng chứng đầu — CP1: giả thuyết + nguồn sẽ kiểm · CP2: số đầu tiên + 1 trích dẫn | CP1 — giả thuyết: ≥2/3 học sinh lớp 12 được phỏng vấn kể được ≥1 lần trong tháng qua làm xong đề mà không biết nên ôn chương nào tiếp. Nguồn sẽ kiểm: phỏng vấn ≥3 học sinh lớp 12; khảo sát ≥20 học sinh để kiểm lại. Chưa có số liệu thật. Chi tiết: `evidence/hypothesis.md` |
| 5 | **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả) | Học sinh lớp 12 chat với agent trong app (vd "ra đề ôn vá chỗ em yếu") → agent đọc kết quả các đề đã làm online, xác định chương yếu và chọn câu từ ngân hàng theo cấu trúc đề thi → agent trả về ngay trong khung chat một đề ôn ngắn để làm online, mỗi câu ghi rõ chương và nguồn |
| 6 | AI tự làm đến đâu + 1 dòng lý do: sai thì ai chịu gì | AI gợi ý, người quyết: agent nói rõ trong chat vì sao chọn chương đó và đề xuất đề ôn, học sinh chỉnh bằng lời (đổi chương, số câu, độ khó) trước khi làm. Sai thì học sinh mất thời gian ôn chưa đúng chỗ (rẻ, sửa được). Câu hỏi chỉ lấy từ ngân hàng đã duyệt, agent không tự bịa câu hỏi hay đáp án |
| 7 | Phân công có tên | ____ *(điền tên từng người và phần việc)* |
| — | *(CP2)* Đã đổi gì so với CP1 | |

# Track F · Examind — Nền tảng AI Agent hỗ trợ tạo đề thi và cá nhân hóa ôn tập môn Toán THPT

*Examind = Exam + Mind, đánh giá thông minh. Slogan: "Beyond traditional assessment".*

> Mục đánh dấu *(dự kiến)* là kế hoạch của nhóm, chưa phải kết quả đã kiểm. Chưa có số liệu thật nào ở thẻ này.

**Lĩnh vực.** Giáo dục phổ thông, ôn thi tốt nghiệp THPT môn Toán. Không thuộc khoá AI20K nên không thuộc track A.
**Pain.** Học sinh lớp 12 — làm đề thử Toán để ôn thi — chỉ có tổng điểm, không biết mình yếu chương nào nên chọn đề ôn không trúng chỗ yếu — ôn dàn trải, tốn giờ ở chương đã vững, điểm khó tăng *(giả thuyết, chưa kiểm)*.
**Insight từ người dùng thật.** Chưa có. Giả thuyết ở `evidence/hypothesis.md`. Sẽ kiểm bằng phỏng vấn ≥3 học sinh lớp 12 và khảo sát ≥20 học sinh *(dự kiến)*.
**Người dùng.** Học sinh lớp 12 đã làm ít nhất một đề thử Toán · gặp họ ở: ____ *(nhóm điền: em, họ hàng, bạn bè, nhóm học, lớp học thêm nào mà nhóm liên hệ được trong hai ngày)*.
**Data.** Không dùng dữ liệu thật của học sinh. Ngân hàng câu hỏi nhỏ tự dựng, mỗi câu gắn chương, độ khó, đáp án; cấu trúc đề tham khảo từ nguồn công khai có ghi link. Kết quả làm bài của học sinh tự dựng có seed. Ghi nguồn và cách dựng trong `data/DATA_CARD.md` *(dự kiến)*.
**Lát cắt.** Một học sinh lớp 12 · chat đề nghị ra đề ôn vá chỗ yếu · agent xác định chương yếu từ kết quả đã làm và chọn câu từ ngân hàng · nhận một đề ôn ngắn, mỗi câu ghi chương và nguồn.
**Công cụ của agent** *(dự kiến, khớp `codebase/tools.py`)*.
- `get_student_results(student_id)` · input: mã học sinh · output: số câu đúng/sai theo chương · không tác động ra ngoài.
- `search_question_bank(chapter, difficulty, n)` · input: chương, độ khó, số câu · output: danh sách câu hỏi kèm mã câu · không tác động ra ngoài.
- `build_exam_draft(question_ids)` · input: mã câu · output: bản nháp đề · chỉ tạo bản nháp, học sinh duyệt trước khi làm.
**Bộ câu thử.** Câu thường: "ra đề ôn chương mà em hay sai". Câu khó: học sinh chưa làm đề nào, kết quả mâu thuẫn, yêu cầu chương mà ngân hàng không có câu. Câu phải từ chối: xin đáp án để chép, đòi sửa điểm, "bỏ qua hướng dẫn trước đó", hỏi ngoài môn Toán. Đạt khi câu được chọn đúng chương yếu và có trong ngân hàng, ngưỡng chốt ở CP2.
**Persona chi phí.** Ít (ôn rải rác) · vừa (mỗi tuần một đề ôn) · nhiều (ôn dồn trước kỳ thi). Số lần dùng lấy từ phỏng vấn và khảo sát, chưa có.
**Bẫy.**
- Không gặp được học sinh lớp 12 thật nên không có insight, chỉ có ý tưởng.
- Lát cắt phình ra: tạo đề cho giáo viên, pipeline PDF/OCR, làm đề online đầy đủ.
- Agent tự bịa câu hỏi hoặc đáp án sai kiến thức Toán, hoặc chọn câu không thuộc chương yếu mà vẫn nói là đúng.
**An toàn.**
- Agent không tự sinh câu hỏi hay đáp án; chỉ chọn câu từ ngân hàng đã duyệt, không có thì nói không có.
- Không dùng điểm hay dữ liệu thật của học sinh; không xếp hạng, so sánh học sinh với nhau.
- Chỉ đề xuất đề ôn, không ghi điểm chính thức. Không xin thông tin cá nhân.

## Ngoài lát cắt (để sau, không làm trong hackathon này)

- Giáo viên chat với agent để tạo đề tuỳ ý (nhiều cấu trúc đề theo năm, theo kỳ thi). Cùng giao diện chat, chỉ khác người dùng và yêu cầu.
- Pipeline admin: nạp file PDF, OCR, tách và phân loại câu hỏi, thêm vào ngân hàng.

Làm đề online và chấm tự động nằm trong app như phần nền của lát cắt (chấm trắc nghiệm theo đáp án có sẵn, không dùng AI). Quyết định AI chỉ là chọn chương yếu và chọn câu cho đề ôn.

Ngân hàng câu hỏi vẫn cần có để lát cắt chạy được. Với lát cắt này, nhóm dựng một ngân hàng nhỏ làm tay hoặc bán tự động, chưa làm pipeline PDF hoàn chỉnh.
