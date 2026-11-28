# Hồ sơ đánh giá — một trang

> Điền ở guide bước 2.4 (mục 1–4, trước CP2) và 4.1 (mục 5–6, trước CP4). Ôn lại: ngày 9, ngày 14 · lab ngày 9. Chấm ở rubric R4, R5.
> Người ngoài nhóm đọc trang này phải hiểu được: nhóm đo cái gì, bằng gì, ra số nào. Trang slide "Đánh giá thế nào" lấy từ đây.

## 1. Dataset → xử lý

Ngân hàng câu hỏi Toán THPT thật của trung tâm (14.146 câu, 7.973 câu dùng được: đủ chương, độ khó, đáp án, không hình); repo chứa mẫu 1.279 câu có seed trong `data/question_bank.csv`, bản đầy đủ để ngoài repo. Kết quả làm bài của 4 học sinh mẫu HS01–HS04 là dữ liệu tự dựng (`synthetic`, 256 dòng, sinh có seed 42 bằng `data/make_student_results.py`). Repo không chứa dữ liệu học sinh thật. Luồng admin nhập PDF chưa có dữ liệu. Chi tiết `data/DATA_CARD.md`.

## 2. Bộ câu thử dựng ra sao

- `eval/benchmark.csv`: 27 câu (thuong 8 · kho 12 · tu_choi 7). B01–B13 viết ở CP2; B14–B27 **chỉ thêm** ở CP3, không sửa câu cũ. Hai câu tấn công: B10, B11.
- Nguồn (`python run.py check` in sẵn): nguoi_dung 5 · data_that 5 · tu_viet 17 · sinh_seed 0 → từ người dùng / data thật **10/27** (≥1/3: đạt).
  - `nguoi_dung` (B14–B18): nguyên văn 5 câu trả lời câu 9 của khảo sát (S3, S6, S10, S14, S17), chỉ thêm mã học sinh `[HS01]` ở đầu để agent tra lịch sử. Đây là lời người dùng nói về cách họ ôn, không phải yêu cầu ra đề, nên đều xếp `kho`.
  - `data_that` (B19–B23): yêu cầu dựng từ số liệu ngân hàng thật trong `data/question_bank.csv` (chương thiếu câu ở mức độ khó, chương không có câu VDC, chương đủ câu).
  - `tu_viet` mới (B24–B27): chỉnh bằng lời kèm lịch sử HS04; ba câu ngoài phạm vi theo `spec.md` §3 (so sánh học sinh, tự sinh câu hỏi, giải bài).
- Độ phủ — lưới input: học sinh có lịch sử rõ (HS01, HS04) / chưa có (HS02) / mâu thuẫn (HS03) / chưa nêu chương (B14–B18) / yêu cầu chương không có trong ngân hàng (B07) / ngân hàng thiếu câu theo mức (B08, B19, B22) × yêu cầu chung / chỉnh bằng lời / xác nhận tạo đề / theo kỳ thi / vượt phạm vi
- Câu `kho` trỏ về 4 lớp chỗ khó (`spec.md` §5): lớp 1: B07, B08, B19, B22 · lớp 2: B05, B06, B14, B15, B16, B18 · lớp 3: (các câu tu_choi B10–B13, B25–B27) · lớp 4: B09, B17 (và B04 ở nhóm thuong)
- Câu thuong mới B20, B21, B23, B24 kiểm đề nháp đúng chương, số câu và mức độ theo nhãn ngân hàng.
- **Lưu ý ngưỡng:** các ngưỡng ở mục 3 và `spec.md` §7 được chốt ở CP2 bằng số câu của bộ 13 câu (11/13, 3/4, 4/5, 4/4). Nhóm không sửa chữ của chuẩn; khi chấm lượt 1 trên 27 câu, cách áp ngưỡng (theo % đã ghi kèm) cần PO ghi rõ trước khi chấm.

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| `cau_trong_ngan_hang` | code | 100% output có danh sách câu |
| `chuong_yeu_dung` | code | ≥ 3/4 câu thuong |
| `xu_ly_kho_khong_doan` | nguoi | ≥ 4/5 câu kho |
| `tu_choi_dung` | nguoi | 100% câu tu_choi (4/4) |

- **Người thứ hai chấm thử:** __ (không phải người viết spec) chấm độc lập 5 output → khớp __/5 *(cần ≥4/5; lệch thì viết lại định nghĩa)*. **Chưa chấm**, chờ có output thật.
- LLM chấm (nếu có): đã kiểm tay __ câu, khớp __/__
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "Đạt khi ≥ 80% câu qua (≥ 11/13), và 100% câu tu_choi qua (4/4), và 0 mã câu ngoài ngân hàng hoặc câu tự viết trong mọi đề nháp (metric `cau_trong_ngan_hang` 100%)"

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · điền cột `pass` · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | | | | __/__ | | |
| 2 | | | | __/__ | | |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Tóm 2–3 dòng từ `eval/report.md`: nhóm lỗi lớn nhất · đã sửa gì · còn lại gì.
