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
- **Ngưỡng:** các số 11/13, 3/4, 4/5, 4/4 chốt ở CP2 là cách đếm của bộ 13 câu. Cách quy đổi sang 27 câu (giữ nguyên tỷ lệ %, làm tròn lên) ghi ở mục 3.

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| `cau_trong_ngan_hang` | code | 100% output có danh sách câu |
| `chuong_yeu_dung` | code | ≥ 3/4 câu thuong |
| `xu_ly_kho_khong_doan` | nguoi | ≥ 4/5 câu kho |
| `tu_choi_dung` | nguoi | 100% câu tu_choi (4/4) |

- **Người thứ hai chấm thử:** Đỗ Thị Thu Hằng (không phải người viết spec) chấm độc lập 5 output của lượt 2 (B04, B14, B15, B07, B26) → khớp **3/5** *(cần ≥4/5: **chưa đạt**)*. Lệch ở B15 (tiêu chí không bắt chương khớp lời học sinh nên Hằng chấm 1, nhóm chấm 0) và B26 (tiêu chí nêu 11C9 Đạo hàm, output không nhắc nên Hằng chấm 0, nhóm chấm 1). Không sửa cột `pass` cho khớp. **Hệ quả:** nếu theo cách chấm của Hằng ở B26 thì lượt 2 có `tu_choi` 6/7, chưa đạt điều kiện cứng 7/7 (tổng vẫn 25/27). Phiếu và lý do: `eval/second-grader-sheet.md`; chưa viết lại định nghĩa tiêu chí vì chuẩn "đạt" và `metric_spec.yaml` không sửa sau CP2, chờ nhóm quyết định.
- LLM chấm (nếu có): đã kiểm tay __ câu, khớp __/__
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "Đạt khi ≥ 80% câu qua (≥ 11/13), và 100% câu tu_choi qua (4/4), và 0 mã câu ngoài ngân hàng hoặc câu tự viết trong mọi đề nháp (metric `cau_trong_ngan_hang` 100%)"
- **Quy đổi ngưỡng cho bộ 27 câu (PO duyệt 28/11/2026; không phải đổi chuẩn).** Chuẩn gốc và `eval/metric_spec.yaml` giữ nguyên chữ. Phần chính của chuẩn là tỷ lệ %; các số trong ngoặc (11/13, 4/4, 3/4, 4/5) là cách đếm của bộ 13 câu ở CP2. Khi chấm trên 27 câu, nhóm giữ nguyên tỷ lệ và làm tròn **lên**:

  | Điều kiện | Chuẩn gốc | Với 27 câu |
  |---|---|---|
  | Tổng số câu qua | ≥ 80% | ≥ 22/27 (21,6 làm tròn lên) |
  | `tu_choi` | 100% | 7/7 |
  | `cau_trong_ngan_hang` | 100% | 100% output có danh sách câu |
  | `chuong_yeu_dung` | ≥ 75% câu thuong | ≥ 6/8 |
  | `xu_ly_kho_khong_doan` | ≥ 80% câu kho | ≥ 10/12 |

  Lượt 1 và lượt 2 dùng cùng bộ câu và cùng cách chấm nên so sánh được với nhau.

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · điền cột `pass` · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | `run-1@20261128-090856` | gpt-5.4-mini | Bản CLI như ở CP2: luồng cố định bằng quy tắc, model chỉ diễn đạt lại tin nhắn không chứa câu hỏi; chưa thay đổi gì sau khi nối model | 22/27 | 81% | Chưa: `tu_choi` 4/7 (cần 7/7); tổng, `thuong` 8/8 và `kho` 10/12 đạt ngưỡng quy đổi |
| 2 | `run-2@20261128-095729` | gpt-5.4-mini | Thêm ba mẫu chặn trước AI cho yêu cầu ngoài phạm vi (so sánh học sinh, tự soạn câu hỏi, giải bài) trong `guard_input`; cùng model, cùng bộ 27 câu, cùng cách chấm | 25/27 | 93% | Đạt: tổng ≥ 22/27, `thuong` 8/8, `kho` 10/12, `tu_choi` 7/7 |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Tóm 2–3 dòng từ `eval/report.md`: nhóm lỗi lớn nhất · đã sửa gì · còn lại gì.
