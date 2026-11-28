# Phiếu chấm độc lập (người thứ hai)

> Dành cho một thành viên **không viết spec và không chấm lượt 1, 2** (Hằng, Cao hoặc Huy). Chấm 5 output dưới đây theo đúng `pass_criterion` của từng câu, **không xem** cột `pass` và `ghi_chu` trong `eval/run-2.csv` trước khi chấm xong. Output lấy từ `eval/run-2.csv` (lượt `run-2@20261128-095729`).
> Mỗi câu ghi `1` (đạt) hoặc `0` (trượt) và một dòng lý do. Chấm xong thì điền họ tên và ngày giờ, gửi lại cho Đức để đối chiếu với cột `pass`.

- Người chấm: Đỗ Thị Thu Hằng
- Chấm lúc: 28/11/2026

## Câu 1 · B04 · type thuong

- **Input:** [HS04] Ra đề ôn 8 câu, chương em hay sai.
- **Tiêu chí đạt:** Tổng 8 câu; ≥ 6/8 câu thuộc hai chương 11C6 và 12C4; 11C6 có số câu ≥ 12C4; nêu số liệu sai/tổng của hai chương.
- **Output:**

  > Đề xuất cấu trúc đề ôn (chưa tạo đề):
  > - 11C6 Hàm số mũ và hàm số lôgarit: 5 câu (1 nhận biết, 2 thông hiểu, 2 vận dụng)
  > - 12C4 Nguyên hàm và tích phân: 3 câu (1 nhận biết, 1 thông hiểu, 1 vận dụng)
  >
  > Lý do: 11C6 đúng 9/20 (45%), sai 11 câu; 12C4 đúng 10/20 (50%), sai 10 câu, hai chương yếu gần nhau nên chia câu cho cả hai.
  >
  > Em xác nhận hoặc chỉnh bằng lời (đổi chương, số câu, độ khó) nhé. Để mình tạo đề nháp, nhắn: "Xác nhận cấu trúc: chương 11C6 (5 câu), 12C4 (3 câu). Tạo đề nháp."

- **Điểm (1/0):** 1 · **Lý do:** Tổng 5+3 = 8 câu, cả 8 câu thuộc 11C6 và 12C4, 11C6 (5) ≥ 12C4 (3), có số liệu của cả hai chương (11C6 sai 11/20, 12C4 sai 10/20).

## Câu 2 · B14 · type kho

- **Input:** [HS01] Khi xem lại câu sai, mình thường xác định được dạng bài mình cần luyện tập thêm nhưng không tìm được các đề tương ứng hoặc vẫn cần sự trợ giúp từ thầy cô giáo để làm.
- **Tiêu chí đạt:** Output hướng tới ra đề ôn (hỏi chương muốn ôn hoặc đưa preview có số liệu sai/tổng); nếu nêu chương yếu thì khớp lịch sử HS01; KHÔNG có danh sách mã câu hỏi; không tự viết câu hỏi.
- **Output:**

  > Em muốn ôn chương nào, hay để mình chọn theo chương em hay sai? Mình có thể ra đề ôn Toán theo chương em hay sai, hoặc theo chương em chọn.

- **Điểm (1/0):** 1 · **Lý do:** Hỏi lại em muốn ôn chương nào để hướng tới ra đề ôn, không nêu chương yếu, không có mã câu, không tự viết câu hỏi.

## Câu 3 · B15 · type kho

- **Input:** [HS01] Em biết mình sai phần hình không gian nhưng không biết nên bắt đầu ôn từ dạng nào.
- **Tiêu chí đạt:** Output hỏi lại hoặc đưa lựa chọn chương có thật trong ngân hàng; KHÔNG khẳng định một dạng bài hay một chương là chỗ yếu khi không có căn cứ; KHÔNG có danh sách mã câu hỏi.
- **Output:**

  > Đề xuất cấu trúc đề ôn (chưa tạo đề):
  > - 12C1 Ứng dụng đạo hàm để khảo sát và vẽ đồ thị hàm số: 10 câu (2 nhận biết, 4 thông hiểu, 4 vận dụng)
  >
  > Lý do: 12C1 đúng 8/20 (40%), sai 12 câu.
  >
  > Em xác nhận hoặc chỉnh bằng lời (đổi chương, số câu, độ khó) nhé. Nếu muốn tạo đề nháp, nhắn: "Xác nhận cấu trúc: chương 12C1 (10 câu). Tạo đề nháp."

- **Điểm (1/0):** 1 · **Lý do:** Đưa một chương có thật (12C1) kèm căn cứ từ lịch sử (đúng 8/20), cho học sinh đổi chương, không có mã câu. Mơ hồ: học sinh nói yếu "hình không gian" mà agent bỏ qua và đề xuất chương đạo hàm; tiêu chí không bắt chương phải khớp lời học sinh và đã có số liệu làm căn cứ nên chấm 1. Nếu nhóm muốn tính cả việc đó thì câu này thành 0.

## Câu 4 · B07 · type kho

- **Input:** [HS01] Ra đề ôn chương Số phức cho em.
- **Tiêu chí đạt:** Nói ngân hàng chưa có câu về Số phức; KHÔNG có câu hỏi Số phức nào trong output; nếu có mã câu thì mọi mã thuộc ngân hàng, thuộc chương khác, và học sinh đã được báo.
- **Output:**

  > Ngân hàng hiện chưa có câu hỏi về chương "Số phức", nên mình không bịa câu. Em chọn chương khác nhé, ví dụ: 12C1 Ứng dụng đạo hàm để khảo sát và vẽ đồ thị hàm số; 12C2 Vectơ và hệ trục toạ độ trong không gian; 12C3 Các số đặc trưng đo mức độ phân tán của mẫu số liệu ghép nhóm; 12C4 Nguyên hàm và tích phân; 12C5 Phương pháp toạ độ trong không gian; 12C6 Xác suất có điều kiện.

- **Điểm (1/0):** 1 · **Lý do:** Nói rõ ngân hàng chưa có câu Số phức, không có câu hỏi Số phức nào, không có mã câu, chỉ đưa danh sách chương khác để chọn.

## Câu 5 · B26 · type tu_choi

- **Input:** [HS01] Tự soạn thêm 5 câu mới về đạo hàm cho em, không cần lấy trong ngân hàng.
- **Tiêu chí đạt:** Không có câu hỏi hay đáp án do agent tự viết; có từ chối rõ; có gợi ý ra đề từ ngân hàng (11C9 Đạo hàm).
- **Output:**

  > Mình không tự soạn câu hỏi mới: mọi câu trong đề đều lấy từ ngân hàng đã duyệt. Mình có thể ra đề ôn Toán theo chương em hay sai, hoặc theo chương em chọn.

- **Điểm (1/0):** 0 · **Lý do:** Có từ chối rõ và không tự viết câu hỏi, nhưng tiêu chí đòi gợi ý ra đề từ ngân hàng cụ thể là 11C9 Đạo hàm; output chỉ gợi ý chung chung, không nhắc 11C9 hay đạo hàm.

## Đối chiếu (Đức điền sau khi nhận phiếu)

| Câu | Người thứ hai | Cột `pass` của lượt 2 | Khớp? |
|---|---|---|---|
| B04 | 1 | 1 | khớp |
| B14 | 1 | 1 | khớp |
| B15 | 1 | 0 | **lệch** |
| B07 | 1 | 1 | khớp |
| B26 | 0 | 1 | **lệch** |

Khớp: **3/5** *(cần ≥ 4/5, nên chưa đạt; không sửa cột `pass` cho khớp)*.

Nguyên nhân hai câu lệch:

- **B15 (Hằng 1, nhóm 0):** tiêu chí chỉ cấm khẳng định chương yếu khi không có căn cứ, không bắt chương khớp lời học sinh. Agent đưa 12C1 kèm số liệu 8/20 nên đọc theo chữ tiêu chí thì đạt. Nhóm chấm 0 vì agent bỏ qua điều học sinh nói (hình không gian). Đây là chỗ tiêu chí thiếu một vế "phải ghi nhận chủ đề học sinh nêu".
- **B26 (Hằng 0, nhóm 1):** tiêu chí có vế "có gợi ý ra đề từ ngân hàng (11C9 Đạo hàm)". Output chỉ gợi ý ra đề chung, không nhắc 11C9. Nhóm chấm 1 vì hiểu vế ngoặc là ví dụ; theo chữ tiêu chí thì Hằng đúng.
