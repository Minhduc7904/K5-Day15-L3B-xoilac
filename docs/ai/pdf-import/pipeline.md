# Pipeline nhập đề PDF

Issue #3 đưa câu hỏi từ đề Toán THPT vào kho chung sau khi admin kiểm tra. Tài liệu này mô tả hợp đồng triển khai và các mốc kiểm chứng.

## Bối cảnh và ràng buộc

Backend dùng PostgreSQL, MinIO và schema nền từ migration `0002`. PDF cần có quyền sử dụng. Mistral trích xuất các trang và hình. OpenAI tách câu, đáp án và lời giải từ nội dung nguồn. Admin xét từng câu trước khi xuất bản.

PDF tối đa 60 trang và 20 MiB. Với tệp trên 30 trang, OCR chạy theo lô tối đa 30 trang rồi khôi phục số trang gốc. Bước tách đề chạy theo lô 4 trang chính và đọc thêm trang liền kề để giữ ngữ cảnh tại ranh giới lô.

## Thành phần và trách nhiệm

| Lớp | Trách nhiệm |
| --- | --- |
| API | Nhận PDF có giới hạn dung lượng, kiểm quyền admin, trả mã phiên và URL theo dõi. |
| Use case | Điều phối các bước, đối chiếu đáp án, kiểm điều kiện duyệt và xuất bản trong một giao dịch. |
| Service | Gọi OCR, Structured Outputs và embedding. Lưu đối tượng qua storage service hiện có. |
| Repository | Lưu phiên, câu nháp và embedding. Dùng chung bảng `media`, `questions`, `statements`, `questions_chapters`. |

## Luồng dữ liệu và tích hợp

1. Lưu PDF gốc và tạo phiên `queued`. Tác vụ nền dùng session DB riêng, đặt trạng thái `processing` rồi cập nhật bước đang chạy.
2. Lưu Markdown từng trang để đối chiếu. Lưu ảnh với quan hệ đến PDF gốc và gắn mã `media:ID` ổn định vào Markdown. Ảnh thiếu hoặc lỗi lưu được báo để admin kiểm tra. Bản nháp có ảnh trong thân câu, lựa chọn hoặc lời giải cần admin xác nhận đã xem ảnh trước khi duyệt.
3. Tách câu và đáp án theo phần và số in trên đề. Giữ thứ tự, LaTeX, trang nguồn, ảnh và lời giải có trong PDF. Gắn cờ đáp án thiếu, mâu thuẫn hoặc ghép không duy nhất. Giá trị chưa rõ của mệnh đề là `null`.

4. So sánh embedding của thân câu và các mệnh đề với một mẫu câu Toán đã xuất bản, có nhãn hợp lệ. Lưu mã câu gần và điểm tương đồng. Để trống nhãn thiếu căn cứ.
5. Trả `ready_for_review` khi có bản nháp hoặc `failed` kèm bước lỗi. Admin sửa, duyệt hoặc bỏ từng câu. Khi duyệt, ghi câu và các liên kết vào kho chung với `visibility=PUBLISHED`. Bản đọc cho học sinh chỉ gồm nội dung, mệnh đề có thứ tự và ảnh được phép đọc.

Khi nhận diện duy nhất khối câu hỏi theo phần và số câu, backend dùng lại Markdown OCR để khôi phục ảnh và cấu trúc lựa chọn. Khối lựa chọn chỉ được khôi phục nếu tìm thấy đủ bốn nhãn theo thứ tự. Với câu có bốn đẳng thức vectơ, backend đối chiếu dấu phẩy trên ký hiệu điểm nếu lớp chữ PDF khớp toàn bộ tên vectơ. Với lời giải đã xác định, backend giữ cả khối một dòng và đọc các kết luận in rõ như “Chọn B”, nhãn đúng/sai, hoặc “Đáp số” dạng số. Đáp án trích từ bảng riêng vẫn được đối chiếu để phát hiện mâu thuẫn.

## Quyết định và cách kiểm chứng

MVP dùng FastAPI BackgroundTasks. Nếu tiến trình dừng trong lúc xử lý, lần tải lại PDF tạo một phiên mới. \`OCR_PROVIDER=mistral\` chọn adapter duy nhất hiện có. \`OCR_MODEL\` chọn model Mistral. Adapter chuyển phản hồi thành danh sách trang có chỉ số bắt đầu từ 0, Markdown và ảnh gồm mã tham chiếu trong Markdown cùng byte ảnh hoặc giá trị thiếu. Bước lưu ảnh và bước tách câu cùng dùng hợp đồng này. Để thêm nhà cung cấp, bổ sung adapter và cấu hình lựa chọn. Tệp gốc và hình nằm trong MinIO riêng tư. URL xem hình có thời hạn đi qua backend để trình duyệt dùng được khi MinIO nằm trong mạng Docker.

| Mốc | Bằng chứng hoàn thành |
| --- | --- |
| 1. Tài liệu và mẫu | Hai tài liệu được viết trước nghiệp vụ. Mẫu PDF chữ có đáp án đã được kiểm. |
| 2. Luồng đầu tiên | Một câu có hình được tải lên, tách, xem ảnh, duyệt và đọc từ kho. |
| 3. Các ca trích xuất và duyệt | Kiểm năm loại câu, số câu lặp, đáp án thiếu hoặc mâu thuẫn, hình trong thân câu, mệnh đề và lời giải. |
| 4. Gợi ý nhãn | Câu gần có mã và điểm tương đồng. Câu thiếu căn cứ được để trống nhãn. |
| 5. Nghiệm thu | Chạy PDF chữ và PDF scan. Kiểm bản đọc sau duyệt và cập nhật ví dụ API. |

- [x] Mốc 1. Đã đối chiếu đề mẫu, trang hình và đáp án. Đã viết tài liệu trước code nghiệp vụ.
- [x] Mốc 2. Đã kiểm từ tải lên đến câu xuất bản và URL ảnh qua API. Test dùng phản hồi nhà cung cấp giả lập và kho tệp trong bộ nhớ.
- [x] Mốc 3. Đã kiểm năm loại câu, số câu lặp, đáp án xung đột, mệnh đề chưa rõ, hình thiếu và câu bị từ chối. Bộ test backend có 49 ca đạt tại mốc này.
- [x] Mốc 4. Đã kiểm gợi ý nhãn, bỏ trống khi điểm thấp, dùng lại embedding đã lưu và bỏ câu bị ngừng xuất bản. Test dùng vector giả lập.
- [x] Mốc 5. Đã chạy PostgreSQL và MinIO thật trong Compose local. Hai tệp fixture có chữ và chỉ có ảnh đi qua upload, xem hình, duyệt và đọc kho dùng chung. Cũng đã kiểm tra lưu embedding và truy vấn tham chiếu trên PostgreSQL. Mistral và OpenAI dùng phản hồi fixture trong các lượt này.
- [x] Mốc 5. Đã chạy hai tệp đại diện với Mistral OCR, OpenAI, PostgreSQL và MinIO thật. Cả hai có 22 câu nháp và 22 đáp án khớp bảng in. Đã kiểm hình, duyệt câu và đọc kho dùng chung.

Mẫu tại máy nhóm `data/example_exam.pdf` có 15 trang. Phần I câu 6 có bốn đồ thị trên trang 2 và đáp án D trên trang 7. Phần I câu 5 qua ranh giới trang 1–2. Bản raster hóa local `data/private/pdf-import-example-scanned.pdf` có cùng 15 trang và hoàn toàn gồm ảnh. Cả hai là tệp local.

Chạy từ thư mục gốc trên Windows bằng `.\.venv\Scripts\python.exe -m pytest -q backend`. Test sinh PDF có lớp chữ và PDF chỉ có ảnh. Các test tách câu dùng phản hồi OCR và OpenAI cố định để tái hiện các trường hợp biên. Để nghiệm thu thật, cấu hình `MISTRAL_API_KEY` và `OPENAI_API_KEY` trong `backend/.env`, chạy backend cùng PostgreSQL và MinIO local, rồi thực hiện luồng trong tài liệu API.

Chỉ mục dùng tối đa 160 dòng tham chiếu từ các câu Toán THPT có `visibility=PUBLISHED` và chương hợp lệ trong bảng nền. Khi phiên mới cần gợi ý, hệ thống bổ sung embedding còn thiếu. Vector được lưu theo mã câu và model, làm mới khi thân câu hoặc mệnh đề đổi. Chỉ các câu hiện còn xuất bản được truy vấn. MVP dùng cosine chính xác, tối đa 5 câu gần, ngưỡng khởi điểm 0,65 và chênh tỷ trọng phiếu 0,12. Các ngưỡng này cần đối chiếu với dữ liệu mẫu qua model thật. Câu phụ thuộc vào hình đi thẳng tới gắn nhãn thủ công.

### Nghiệm thu live ngày 28/11/2026

| Đầu vào | Câu nháp theo phần I / II / III | Đáp án khớp bảng in | Câu có gợi ý chương | Câu có lời giải giữ lại |
| --- | --- | --- | --- | --- |
| PDF có lớp chữ, 15 trang | 12 / 4 / 6 | 22/22 | 11 | 11 |
| PDF raster hóa, 15 trang | 12 / 4 / 6 | 22/22 | 11 | 17 |

Một trang PDF scan đi qua Mistral với HTTP 200. Câu 6 giữ phân số `(2x+1)/(x+4)` và đủ bốn đồ thị. Cả hai phiên đầy đủ mở được ảnh A–D qua URL ký, ghi D theo bảng in và chặn duyệt đến khi admin xác nhận ảnh và nhãn. Câu đã duyệt đọc được từ kho với nội dung và thứ tự lựa chọn. Bản đọc dành cho học sinh ẩn đáp án.

Lượt kiểm phát hiện OCR đưa nhãn A–D xuống sau ảnh, model đưa đoạn thân câu vào danh sách lựa chọn, và một số dòng bảng đáp án bị gán sai trang. Pipeline chuẩn hóa thứ tự ảnh trước khi tách, chỉ sửa ranh giới lựa chọn khi có dấu hiệu A–D trong nguồn và định vị lại dòng bảng đáp án khi khớp duy nhất. Test hồi quy kiểm cả ca bảng có dòng lặp.

Tổng lượt kiểm gồm 30 trang Mistral, 29.967 token đầu vào và 26.337 token đầu ra khi tách câu, cùng 12.315 token embedding. Chi phí ước tính theo biểu giá chuẩn là **0,2612 USD**. Con số gồm các lượt kiểm và chạy lại sau sửa. Hai trang scan từ lượt kiểm ban đầu được ghép lại theo thứ tự khi chạy đề đủ. Các lượt kiểm sau tái sử dụng kết quả OCR đã lưu. [Giá Mistral OCR](https://docs.mistral.ai/models/ocr-4-1) · [Giá GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini) · [Giá embedding](https://developers.openai.com/api/docs/models/text-embedding-3-small)

Các đề được đối chiếu theo bảng đáp án in trên tài liệu. Sau lượt live trên, lượt kiểm lại bằng OCR và kết quả trích xuất đã lưu giữ được **22/22 lời giải cho mỗi PDF**. Backend chép Markdown theo tiêu đề lời giải, phần và số câu, ghi đủ các trang qua `solutionPages` và gắn cờ `solution_review` khi thiếu căn cứ. Với khối đã chép, OpenAI chỉ cần trích dẫn đoạn ngắn và kết quả đã in để đối chiếu đáp án. Lượt kiểm lại không gọi API.

Gợi ý nhãn đôi khi sai chương dù có điểm tương đồng cao, nên vẫn cần admin xác nhận. Bản scan là bản raster hóa cùng đề. Chất lượng trên bản chụp giấy, bố cục lời giải khác và ngân hàng chương rộng hơn cần kiểm thêm.

### Tích hợp Auth, migration và danh mục chương

API nhập đề dùng chung kiểm tra vai trò admin của Auth. URL đọc hình và PDF vẫn hết hạn sau 5 phút. Issue #4 đọc câu đã xuất bản qua kho câu hỏi dùng chung.

Revision Alembic `0007_pdf_import_auth` nối hai nhánh `0004` (Auth) và `0004_pdf_import_vectors` (nhập đề). Lượt kiểm PostgreSQL ban đầu nâng DB trắng, DB đã chạy Auth và DB đã chạy nhập đề về revision này. Sau khi `main` thêm `0005_student_auth`, revision `0008_pdf_import_student_auth` nối hai head và giữ nguyên lịch sử migration. Đã nâng cấp PostgreSQL local từ DB trắng và DB ở `0005_student_auth` lên cùng một head mới.

#5 và #4 đã vào `main`. Revision `0009_pdf_import_exam_templates` nối `0005_exam_templates` với `0008_pdf_import_student_auth`. Revision `0010_pdf_import_exam_chat` nối head này với `0006_exam_chat` của #4. Các revision đã có giữ nguyên quan hệ phụ thuộc. Kiểm tra một head duy nhất bằng `alembic heads` và chạy `alembic upgrade head` trước khi triển khai.

Đã nạp và đọc lại đủ 103 mã chương từ `data/chapters.csv` trên PostgreSQL local. Cả 1.279 câu mẫu trong `data/question_bank.csv` dùng mã hợp lệ và quan hệ chương–chương con khớp danh mục. Danh mục trên VPS chưa được đối chiếu vì máy này chưa có host key SSH đã xác minh.

## Tài liệu liên quan

- [API nhập đề PDF](api.md)
- [Các lớp backend](../../architecture/backend-layers.md)
- [Chạy bộ khung local](../../operations/run-local-stack.md)
- [Issue #3](https://github.com/Minhduc7904/K5-Day15-L3B-xoilac/issues/3)
