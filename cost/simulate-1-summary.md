# Tóm tắt mô phỏng simulate-1@20261128-100201

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| on_rai_rac | 23 | 2 | 252 | 136 | 1.2 | 2.5 |
| on_deu | 16 | 3 | 409 | 216 | 1.9 | 3.7 |
| on_don_truoc_ky_thi | 11 | 4 | 501 | 266 | 2.4 | 8.2 |

Tỉ lệ đạt dùng để tính: 25/27 (93%) — lượt run-2@20261128-095729

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-2.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (100 người) | Chi phí / tháng — cơ sở (500 người) | Chi phí / tháng — cao (2.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-5.4-mini (vào 0.75 · ra 4.5 $/1M) | $0.0011 | $0.0012 | $0.00044 | $0.2619 | $1.31 | $5.24 | $0.0026 |
| gpt-5-nano (vào 0.05 · ra 0.4 $/1M) | $0.000094 | $0.00010 | $0.000037 | $0.0219 | $0.1095 | $0.4379 | $0.00022 |
| gpt-6.2-sol (vào 2.0 · ra 10.0 $/1M) | $0.0026 | $0.0028 | $0.0010 | $0.6098 | $3.05 | $12.20 | $0.0061 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.8) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gpt-5.4-mini. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
