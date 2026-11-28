# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu.

  | Persona | Tỉ lệ | Phiên / người / tháng | Lượt hỏi / phiên | Nguồn |
  |---|---|---|---|---|
  | `on_rai_rac` | 0,5 | 1 | 2 | Số phiên: khảo sát câu 8, 8/14 phiếu có nêu số lần ôn 1 lần/tháng. Tỉ lệ và số lượt: *(tự ước tính)* |
  | `on_deu` | 0,3 | 2,5 | 3 | Số phiên: khảo sát câu 8, 6/14 phiếu ôn 2–3 lần/tháng, lấy giữa khoảng. Tỉ lệ và số lượt (yêu cầu, chỉnh bằng lời, xác nhận như B01–B03): *(tự ước tính)* |
  | `on_don_truoc_ky_thi` | 0,2 | 4 | 4 | *(Tự ước tính)*: khảo sát không hỏi riêng nhóm này |

  Khảo sát: `evidence/survey/results.csv` (23 phiếu, một trung tâm). Mỗi lượt hỏi lấy ngẫu nhiên một đầu vào `thuong` hoặc `kho` trong `eval/benchmark.csv`.
- **Số người dùng thật** 3 kịch bản: thấp 100 · cơ sở 500 · cao 2.000. Nguồn: *(tự ước tính)*, nhóm chưa có số học sinh thật của trung tâm (không dùng số khoá học của đề mẫu). Mốc tham chiếu công khai: cả nước có 2.993.731 học sinh THPT năm học 2023-2024 ([giaoduc.net.vn](https://giaoduc.net.vn/gdvn-post244337.gd)), nên mốc cao 2.000 ≈ 0,07% số đó.
- **Giá** ≥2 mức model (từ `further-reading/model-prices.md` của repo đề, USD / 1 triệu token, xem 25/11/2026, trang giá [OpenAI](https://developers.openai.com/api/docs/pricing)): gpt-5-nano vào 0,05 · ra 0,40 · gpt-5.4-mini vào 0,75 · ra 4,50 · gpt-6.2-sol vào 2,00 · ra 10,00.
- **Tỉ lệ đạt** dùng để tính: 25/27 (93%) — lượt `run-2@20261128-095729` (lượt 2, `--rate-from eval/run-2.csv`)
- Đo token trên model **gpt-5.4-mini**, tính giá model gpt-5.4-mini (đúng model đã đo), và gpt-5-nano, gpt-6.2-sol (chỉ nhân giá với token đo ở gpt-5.4-mini; hai model này chưa chạy eval nên chưa biết tỉ lệ đạt của chúng).

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID `simulate-1@20261128-100201` · 50 phiên · seed 42 · 0/50 phiên lỗi

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| on_rai_rac | 23 | 2 | 252 | 136 | 1.2 | 2.5 |
| on_deu | 16 | 3 | 409 | 216 | 1.9 | 3.7 |
| on_don_truoc_ky_thi | 11 | 4 | 501 | 266 | 2.4 | 8.2 |

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp (100 người) | / tháng — cơ sở (500 người) | / tháng — cao (2.000 người) | / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|
| gpt-5.4-mini (vào 0.75 · ra 4.5) | $0.0011 | $0.0012 | $0.2619 | $1.31 | $5.24 | $0.0026 |
| gpt-5-nano (vào 0.05 · ra 0.4) | $0.000094 | $0.00010 | $0.0219 | $0.1095 | $0.4379 | $0.00022 |
| gpt-6.2-sol (vào 2.0 · ra 10.0) | $0.0026 | $0.0028 | $0.6098 | $3.05 | $12.20 | $0.0061 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt (93%) — **không coi như đạt 100%**.

Hai chỗ cần đọc kèm:

- Token ít vì bản CLI chỉ dùng model để diễn đạt lại tin nhắn; luồng chọn chương và dựng đề chạy bằng quy tắc, không tốn token. Nhiều phiên chỉ gọi model 1–2 lần (một phiên, S049, chặn trước AI nên 0 token). Luồng web ở backend cho model chọn công cụ và đề xuất chương, tốn token hơn; **nhóm chưa đo luồng đó**, nên bảng này là cận dưới cho bản đang nộp.
- Phiên chạy bằng bộ câu thử nên có thể giống nhau hơn người thật, và token đo ở 50 phiên, không phải người dùng thật.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): ≈ 0,39 giờ ≈ 23 phút / học sinh (39 giờ / 100 học sinh), từ 82,6% học sinh gặp × 1,43 lần × 20 phút *(phút là tự ước tính)*.
- Chi phí / người / tháng (cơ sở, model gpt-5.4-mini): $0.0026 (khoảng 0,26 US cent; mức cao nhất trong bảng, gpt-6.2-sol, là $0.0061).
- **Kết luận một dòng — đáng làm không:** Với bản đang đo, chi phí model chỉ cỡ vài phần nghìn USD mỗi học sinh mỗi tháng, rất nhỏ so với khoảng 23 phút tiết kiệm *(tự ước tính)*, nên đáng làm về tiền model; kết luận này chưa tính hosting, giờ người duyệt câu hỏi và luồng web dùng nhiều token hơn bản đo.

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Độ nhạy theo model (cùng token đo): gpt-5-nano rẻ hơn gpt-5.4-mini ≈ 12 lần; gpt-6.2-sol đắt hơn ≈ 2,3 lần. Chọn nano chỉ có nghĩa nếu chạy lại eval trên nano mà tỉ lệ đạt không tụt.
- Chi phí ngoài model: hosting (EC2), lưu trữ MinIO, giờ công admin duyệt câu hỏi mới. Nhóm chưa tính.
- Chưa thử cache, cắt ngữ cảnh hay giới hạn bước.
