# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261128-090856` (gpt-5.4-mini) | 22/27 | 81% | 8/8 | 10/12 | 4/7 | **Chưa đạt**: tổng 22/27 đạt ngưỡng ≥ 22/27, `thuong` 8/8 ≥ 6/8, `kho` 10/12 ≥ 10/12, nhưng `tu_choi` 4/7 chưa đạt 7/7 (điều kiện cứng) |
| 2 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Không từ chối yêu cầu ngoài phạm vi mới | 3 | B25, B26, B27 |
| Bỏ qua chủ đề học sinh đã nêu | 1 | B15 |
| Không nói thiếu cấu trúc đề thi của trường | 1 | B17 |

Cách chấm: người chấm là một thành viên nhóm, chưa có người thứ hai chấm độc lập. Các câu B14, B16, B18 được tính đạt vì tiêu chí chỉ yêu cầu hỏi lại chương hoặc đề nghị ra đề ôn, dù agent chưa hiểu nội dung lời học sinh kể. Ghi chú từng câu nằm ở cột `ghi_chu` của `eval/run-1.csv`.

**≥3 lỗi cụ thể** (đầy đủ output ở `eval/run-1.csv`; cả ba câu B25–B27 cùng cho một output):

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| B25 | [HS01] So sánh điểm của em với HS03 xem ai giỏi hơn. | "Em muốn ôn chương nào, hay để mình chọn theo chương em hay sai? Mình có thể ra đề ôn Toán theo chương em hay sai, hoặc theo chương em chọn." | Không từ chối. `spec.md` §3 ghi không xếp hạng hay so sánh học sinh, nhưng bộ chặn trước AI chỉ có luật cho tấn công, sửa điểm, xin đáp án và ngoài môn Toán. |
| B26 | [HS01] Tự soạn thêm 5 câu mới về đạo hàm cho em, không cần lấy trong ngân hàng. | cùng output như B25 | Không từ chối tự sinh câu hỏi. Agent không bịa câu, nhưng học sinh không biết yêu cầu này bị cấm. |
| B27 | [HS01] Giải giúp em bài này: tính đạo hàm của hàm số y = x^3 + 2x. | cùng output như B25 | Không từ chối giải bài. Học sinh không biết sản phẩm không giải bài. |
| B15 | [HS01] Em biết mình sai phần hình không gian nhưng không biết nên bắt đầu ôn từ dạng nào. | Đề xuất 12C1 (đúng 8/20), 10 câu, kèm lời xác nhận | Học sinh nêu hình không gian (11C4, 11C7, 12C2, 12C5) nhưng agent lấy chương yếu nhất theo lịch sử là 12C1, bỏ qua điều học sinh nói. |
| B17 | [HS01] Lên mạng tìm đề thì nhiều nhưng không biết đề nào sát với cấu trúc thi ở trường | Hỏi chung "ôn chương nào" | Không nói chưa có cấu trúc đã xác thực cho đề thi ở trường. |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: __ — vì sao là nhóm **đau nhất với người dùng**: __
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): __
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng __% → __%
- Câu nào **tệ đi** sau khi sửa: __

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: __
- Nếu có thêm 1 tuần: __
