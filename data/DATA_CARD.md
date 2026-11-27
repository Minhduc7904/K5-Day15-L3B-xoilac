# Data card — dữ liệu bản chạy thử dùng

> Bản CP2 (27/11/2026). Nhóm có dữ liệu thật từ một trung tâm dạy thêm do một thành viên nhóm làm quản lý. Repo chỉ chứa **một mẫu nhỏ của dữ liệu câu hỏi** (1.279 câu); bản đầy đủ để ở máy nhóm, không commit. Không có dữ liệu học sinh thật, bản chạy thử dùng hồ sơ học sinh tự dựng.
> Các cột `__` là chỗ nhóm điền khi dựng xong. Bằng chứng pain nằm ở `evidence/`, không nằm ở file dữ liệu này.

## Dataset 1 · Ngân hàng câu hỏi Toán THPT (`data/question_bank.csv` là mẫu, `data/chapters.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `search_question_bank` và `build_exam_draft`; căn cứ để kiểm "mã câu có trong ngân hàng" (metric `cau_trong_ngan_hang`); nguồn câu cho luồng embedding và vector DB |
| Từ đâu | Câu hỏi Toán THPT của một trung tâm dạy thêm do một thành viên nhóm làm quản lý, lấy từ bản sao lưu hệ thống của trung tâm ngày 27/11/2026 |
| Cột `question_bank.csv` | `ma_cau` · `lop` (10/11/12) · `chuong` (mã chương cấp 0, vd `12C4`) · `chuong_con` (mã chương cấp 1) · `do_kho` (`NB` nhận biết, `TH` thông hiểu, `VD` vận dụng, `VDC` vận dụng cao) · `loai` (`SINGLE_CHOICE`, `TRUE_FALSE`, `SHORT_ANSWER`, `MULTIPLE_CHOICE`) · `noi_dung` (LaTeX) · `lua_chon` (JSON, kèm nhãn đúng/sai) · `dap_an` · `co_hinh` · `da_duyet` |
| Cột `chapters.csv` | `ma_chuong` · `ten` · `ma_chuong_cha` · `cap` · `lop`; cây chương trình Toán 10, 11, 12 (9 + 9 + 6 chương cấp 0) |
| Xử lý những bước gì | Xuất các câu môn Toán, trạng thái đã đăng (`PUBLISHED`) sang CSV (bản đầy đủ 14.146 câu để ở máy nhóm, ngoài repo). Ghép chương từ bảng liên kết câu–chương. **Lấy mẫu cho repo:** chỉ giữ câu dùng được (đủ chương, độ khó, đáp án, không hình), chia nhóm theo chương cấp 0 × độ khó, mỗi nhóm lấy khoảng 15% (tối thiểu 5 câu hoặc cả nhóm nếu ít hơn), ngẫu nhiên có seed 42. `dap_an`: lấy ô đáp án gốc nếu có, nếu trống thì suy từ các lựa chọn được đánh dấu đúng (chữ cái với câu trắc nghiệm, chuỗi Đ/S với câu đúng–sai). Không đưa lời giải vào. Không có dữ liệu học sinh. Không sửa nội dung câu |
| Số dòng | Mẫu trong repo: **1.279 câu** (24 chương cấp 0, mỗi chương 11–177 câu) · `chapters.csv`: 103 chương. Bản đầy đủ: 14.146 câu |
| Phân bố | **Mẫu trong repo (1.279 câu, đều là câu dùng được):** lớp 10: 304 · lớp 11: 458 · lớp 12: 517 · NB 304 · TH 333 · VD 538 · VDC 104. **Bản đầy đủ (ngoài repo):** có chương 10.328 · có độ khó 11.550 · có `dap_an` 14.030 · có hình 3.168 · dùng được 7.973 |
| Phiên bản / ngày lấy | Bản sao lưu 27/11/2026 |
| Nhãn | Thật (dữ liệu của trung tâm), không phải `synthetic` |
| Giới hạn | Chương và độ khó do trung tâm gắn, nhóm chưa kiểm với giáo viên *(chưa kiểm)*. `dap_an` suy từ lựa chọn khi ô gốc trống, chưa kiểm tay. Hình minh hoạ chỉ có tham chiếu `media:ID`, ảnh không nằm trong repo nên câu có hình bị loại khỏi phần "dùng được". 3.818 câu chưa gắn chương và 2.596 câu chưa có độ khó. Có chương chỉ có rất ít câu dùng được (vd `10C53`: 1 câu). Mẫu giữ tỉ lệ theo bản đầy đủ nên lệch về lớp 12 và chương `12C1`, `12C4`, và có ít câu `VDC` (ví dụ `12C1`: 13 câu). Không có chương Số phức (chương trình mới). Số đo trên mẫu không đại diện cho bản đầy đủ. Không đại diện cho đề thi chính thức |

**Dữ liệu khác của trung tâm.** Nhóm còn có dữ liệu vận hành khác của trung tâm; không đưa vào repo và không dùng cho bộ câu thử.

## Dataset 2 · Kết quả làm bài của học sinh mẫu (`data/student_results.csv`)

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `get_student_results`; căn cứ tính chương yếu và chấm metric `chuong_yeu_dung` |
| Từ đâu | Sinh có seed bằng `data/make_student_results.py` (chạy `python data/make_student_results.py`, seed 42, chỉ dùng thư viện chuẩn). Học sinh là mã giả `HS01`–`HS04`, các `ma_cau` lấy từ câu dùng được của Dataset 1. Không lấy từ học sinh thật |
| Cột | `ma_hs` · `luot` (lượt làm đề) · `ma_cau` · `chuong` · `ket_qua` (`dung` / `sai`) |
| Hồ sơ (bộ câu thử dựa vào đây) | **HS01:** 4 lượt, chương yếu nhất `12C1` (khoảng 40% đúng), các chương khác ≥ 70% (B01, B02, B03, B07, B08) · **HS02:** chưa có dòng nào (B05) · **HS03:** nhiều câu có hai dòng cùng `luot` và cùng `ma_cau` nhưng `ket_qua` trái nhau (32/48 câu, 67%), nên không xác định được chương yếu. Quy ước "mâu thuẫn": ≥ 25% số câu của học sinh có kết quả trái nhau trong cùng lượt (B06) · **HS04:** hai chương yếu gần nhau, `11C6` (khoảng 45% đúng) và `12C4` (khoảng 50%), các chương khác ≥ 75% (B04) |
| Xử lý những bước gì | Chỉ ghi đúng/sai theo câu và chương; không lưu điểm chính thức; không có thông tin cá nhân |
| Số dòng | 256 (HS01: 80 · HS03: 80 · HS04: 96 · HS02: 0). Chương dùng mã cấp 0 trong `chapters.csv` |
| Phiên bản / ngày lấy | Sinh ngày 27/11/2026 · seed 42 |
| Nhãn | `synthetic` |
| Giới hạn | Hồ sơ dựng theo tình huống cần thử nên sạch hơn thực tế; không phản ánh phân bố lỗi của học sinh thật; không kết luận được tần suất hay mức độ pain từ dữ liệu này |

**Cách sinh và kiểm:** script `data/make_student_results.py` · seed 42 · chạy 3 lần ra cùng file (md5 trùng) · script in tỉ lệ đúng/sai từng chương và khớp bảng hồ sơ ở trên (HS01 `12C1` 8/20 = 40%, các chương khác 75–83%; HS04 `11C6` 9/20 = 45%, `12C4` 10/20 = 50%, các chương khác ≥ 80%). Chưa có người kiểm tay (`__`).

## Dataset 3 · Đề PDF do admin nhập (dự kiến, **ngoài lát cắt CP2**)

| | |
|---|---|
| Dùng để làm gì | Luồng admin: nhập PDF, tách chữ, tách từng câu, so embedding với ngân hàng để gợi ý chương và độ khó, admin duyệt rồi mới đưa vào ngân hàng |
| Từ đâu | PDF do admin tải lên, chỉ từ nguồn có quyền dùng. Chưa có file nào trong repo |
| Số dòng / phiên bản | Chưa dựng |
| Nhãn | Chưa có dữ liệu |
| Giới hạn | Tách chữ từ PDF Toán dễ sai công thức; độ khó do embedding gợi ý có thể lệch nên admin phải duyệt. Chưa kiểm vì chưa dựng |

Dữ liệu này không nằm trong bộ câu thử CP2, không có số đo nào cho luồng này.
