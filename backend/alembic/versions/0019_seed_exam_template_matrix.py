"""Nạp mẫu cấu trúc đề (ma trận) môn Toán: THPT 2025, THPT 2026 và GK1/CK1/GK2/CK2 của khối 10, 11, 12.

Dữ liệu vào bảng `exam_templates` (migration 0005). Mã chương (`chapter_codes`) khớp `data/chapters.csv`
(10C1 ... 12C6). Gói seed nền được nạp SAU migration nên không ràng buộc khoá ngoại, chỉ dùng mã chuỗi.

NGUỒN VÀ ĐỘ TIN CẬY (ghi thêm trong cột `source` và `description` của từng mẫu):
- THPT 2025 và 2026: cấu trúc công khai 12 trắc nghiệm / 4 đúng-sai / 6 trả lời ngắn, 90 phút, 34 ý hỏi. Chỉ có
  cấu trúc tổng và phạm vi chương. KHÔNG tìm được ma trận chính thức theo từng chương (bản của Bộ ở dạng ảnh, một số
  trang trả 403), nên không bịa số câu theo chương.
- Giữa kỳ / cuối kỳ: Bộ không ban hành một ma trận chung, mỗi trường tự ra. Chỉ có Toán 11 GK1 2025-2026 (THPT Ngô Gia Tự,
  Đắk Lắk) đọc được đầy đủ; Toán 12 theo cấu trúc đề tốt nghiệp (tuyensinhso.vn). Các mẫu còn lại là *(tự ước tính)*:
  cấu trúc lấy theo mẫu gần nhất, phạm vi chương theo phân phối chương sách Kết nối tri thức (khớp data/chapters.csv).
- Mọi mẫu giữa kỳ / cuối kỳ nạp ở trạng thái DRAFT để admin xem lại rồi duyệt. Mẫu THPT nạp APPROVED vì cấu trúc
  tổng được nhiều nguồn báo chí xác nhận.

Chạy lại nhiều lần không sinh dòng trùng (khoá theo name + exam_type + version_label). Downgrade chỉ xoá đúng các dòng
do migration này nạp.

Revision ID: 0019_seed_exam_template_matrix
Revises: 0018_chat_session_title
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0019_seed_exam_template_matrix"
down_revision = "0018_chat_session_title"
branch_labels = None
depends_on = None

NLC, DS, TLN, TL = "SINGLE_CHOICE", "TRUE_FALSE", "SHORT_ANSWER", "ESSAY"


def _chapters(grade: int, nums: list[int]) -> list[str]:
    return [f"{grade}C{n}" for n in nums]


def _section(order, title, qtype, count, points=None, dist=None, chapters=None) -> dict:
    s = {"order": order, "title": title, "question_type": qtype, "count": count}
    if points is not None:
        s["points_per_question"] = points
    if dist is not None:
        s["difficulty_distribution"] = dist
    if chapters is not None:
        s["chapter_codes"] = chapters
    return s


# ---------------------------------------------------------------- THPT 2025 / 2026
G12_ALL = _chapters(12, [1, 2, 3, 4, 5, 6])
# Lớp 11 xuất hiện ở phần II, III (báo Đại biểu Nhân dân 18/10/2024: hình học không gian, lượng giác, dãy số/CSC/CSN,
# mũ-lôgarit, xác suất): 11C1 lượng giác, 11C2 dãy số, 11C4 + 11C7 hình học không gian, 11C6 mũ-lôgarit, 11C8 xác suất.
G11_IN_THPT = ["11C1", "11C2", "11C4", "11C6", "11C7", "11C8"]


def _thpt_sections(extra_part3: list[str]) -> list[dict]:
    return [
        _section(1, "Phần I. Trắc nghiệm nhiều phương án lựa chọn", NLC, 12, 0.25, None, G12_ALL),
        _section(2, "Phần II. Trắc nghiệm đúng/sai (mỗi câu 4 ý)", DS, 4, 1.0, None, G12_ALL + G11_IN_THPT),
        _section(3, "Phần III. Trắc nghiệm trả lời ngắn", TLN, 6, 0.5, {"VD": 6}, G12_ALL + G11_IN_THPT + extra_part3),
    ]


THPT_2025 = {
    "name": "Tốt nghiệp THPT 2025 – Toán",
    "exam_type": "THPT",
    "grade": 12,
    "version_label": "2025",
    "duration_minutes": 90,
    "source": (
        "Đề tham khảo Toán tốt nghiệp THPT 2025 của Bộ GD&ĐT, theo báo Đại biểu Nhân dân (18/10/2024): "
        "https://daibieunhandan.vn/de-tham-khao-mon-toan-tot-nghiep-thpt-2025-dam-bao-phan-hoa-ro-nang-luc-thi-sinh-10349516.html"
    ),
    "description": (
        "22 câu = 34 ý hỏi: 12 trắc nghiệm nhiều lựa chọn (0,25 đ/câu, nhận biết–thông hiểu), 4 câu đúng/sai x 4 ý "
        "(điểm tối đa 1 đ/câu; đúng 1/2/3/4 ý được 0,1/0,25/0,5/1 đ), 6 câu trả lời ngắn (0,5 đ/câu, vận dụng). "
        "Nhận biết–thông hiểu 25/34 ý (khoảng 73%, ~6 đ), vận dụng 9 ý (~4 đ). Kiến thức: lớp 12 khoảng 70% (22 ý), "
        "lớp 11 khoảng 30% (12 ý). chapter_codes của mỗi phần là PHẠM VI chương có thể xuất hiện, không phải số câu theo "
        "chương: chưa có nguồn công bố bảng số câu theo chương nên không ghi."
    ),
    "sections": _thpt_sections([]),
}

THPT_2026 = {
    "name": "Tốt nghiệp THPT 2026 – Toán",
    "exam_type": "THPT",
    "grade": 12,
    "version_label": "2026",
    "duration_minutes": 90,
    "source": (
        "Cấu trúc 2026 giữ như 2025: tuyensinhso.vn (cập nhật 23/04/2026) "
        "https://tuyensinhso.vn/tin-moi/ma-tran-de-thi-tham-khao-tot-nghiep-thpt-2025-tat-ca-cac-mon-c345401.html ; "
        "VietnamPlus 11/06/2026 (đề thi thật: 22 câu, 34 lệnh hỏi, cấu trúc ổn định) "
        "https://www.vietnamplus.vn/giao-vien-nhan-dinh-de-toan-tpht-2026-khong-kho-pho-diem-du-kien-trong-khoang-6-65-diem-post1116029.vnp"
    ),
    "description": (
        "Cùng cấu trúc 12 / 4 / 6 như 2025, 90 phút. Điểm mỗi câu theo thể lệ 2025 (không có văn bản 2026 đọc được, "
        "nguồn nói giữ nguyên). Nhận định của một giáo viên về đề thật: phần trả lời ngắn có 2 câu về đếm, tổ hợp, xác suất "
        "(nên thêm 10C8, 10C9 vào phạm vi phần III; chưa kiểm chứng với đề chính thức). Không có ma trận chính thức theo chương: "
        "chapter_codes là phạm vi, không phải số câu theo chương."
    ),
    "sections": _thpt_sections(["10C8", "10C9"]),
}

# ---------------------------------------------------------------- Giữa kỳ / cuối kỳ
# Phân phối chương (sách KNTT, khớp data/chapters.csv): HK1 / HK2.
SEMESTER_CHAPTERS = {
    10: {"GK1": [1, 2, 3], "CK1": [1, 2, 3, 4, 5], "GK2": [6, 7], "CK2": [6, 7, 8, 9]},
    11: {"GK1": [1, 2, 3], "CK1": [1, 2, 3, 4], "GK2": [5, 6], "CK2": [5, 6, 7, 8, 9]},
    12: {"GK1": [1, 2], "CK1": [1, 2, 3], "GK2": [4, 5], "CK2": [4, 5, 6]},
}
EXAM_LABEL = {"GK1": "Giữa kỳ 1", "CK1": "Cuối kỳ 1", "GK2": "Giữa kỳ 2", "CK2": "Cuối kỳ 2"}
YEAR = "2025-2026"

SRC_G12 = (
    "Cấu trúc theo đề tốt nghiệp THPT từ 2025 (90 phút; 12 nhiều lựa chọn 0,25 đ; 4 đúng/sai tối đa 1 đ; 6 trả lời ngắn "
    "0,5 đ): tuyensinhso.vn, Bộ đề kiểm tra giữa kỳ 1 lớp 12 môn Toán (19/10/2024) "
    "https://tuyensinhso.vn/ban-tin/bo-de-kiem-tra-giua-ky-1-lop-12-mon-toan-theo-chuong-trinh-moi-c345111.html ; "
    "chương HK1 theo https://tuyensinhso.vn/tin-moi/de-cuong-on-thi-hoc-ki-1-lop-12-mon-toan-theo-chuong-trinh-moi-c345073.html . "
    "Chỉ GK1 có nguồn; CK1, GK2, CK2 và phạm vi chương HK2 là (tự ước tính)."
)
SRC_NGT = (
    "Ma trận GK1 Toán 11 năm học 2025-2026, THPT Ngô Gia Tự (Đắk Lắk): "
    "https://thpt-ngogiatu-daklak.edu.vn/wp-content/uploads/2025/10/Ma-tran-GK1-Toan-11-nam-2025-2026.docx . "
    "Ma trận của một trường, không phải quy định chung của Bộ."
)


def _semester_sections(grade: int, exam: str) -> list[dict]:
    ch = _chapters(grade, SEMESTER_CHAPTERS[grade][exam])
    if grade == 12:
        return [
            _section(1, "Phần I. Trắc nghiệm nhiều phương án lựa chọn", NLC, 12, 0.25, None, ch),
            _section(2, "Phần II. Trắc nghiệm đúng/sai (mỗi câu 4 ý)", DS, 4, 1.0, None, ch),
            _section(3, "Phần III. Trắc nghiệm trả lời ngắn", TLN, 6, 0.5, None, ch),
        ]
    # Lớp 10, 11: 12 nhiều lựa chọn (3 đ) + 3 đúng/sai (3 đ) + 4 trả lời ngắn (2 đ) + 3 tự luận (2 đ).
    # Nhận biết/thông hiểu của GK1 lớp 11 đọc được từ ma trận Ngô Gia Tự; các mẫu khác để trống.
    gk1_11 = grade == 11 and exam == "GK1"
    return [
        _section(1, "Phần I. Trắc nghiệm nhiều phương án lựa chọn", NLC, 12, 0.25, {"NB": 7, "TH": 5} if gk1_11 else None, ch),
        _section(2, "Phần II. Trắc nghiệm đúng/sai (mỗi câu 4 ý)", DS, 3, 1.0, None, ch),
        _section(3, "Phần III. Trắc nghiệm trả lời ngắn", TLN, 4, 0.5, {"NB": 1, "TH": 3} if gk1_11 else None, ch),
        _section(4, "Phần IV. Tự luận (tổng 2,0 điểm)", TL, 3, None, None, ch),
    ]


def _semester_description(grade: int, exam: str) -> str:
    if grade == 12:
        return (
            "22 câu, 90 phút. Phạm vi chương theo phân phối chương HK1: Ứng dụng đạo hàm (12C1), Vectơ và hệ trục tọa độ "
            "trong không gian (12C2), Số đặc trưng đo mức độ phân tán (12C3); HK2: Nguyên hàm-tích phân (12C4), Oxyz (12C5), "
            "Xác suất có điều kiện (12C6). Chưa có số câu theo chương hay mức độ nhận thức: cần admin bổ sung theo ma trận "
            "của trường."
        )
    if grade == 11 and exam == "GK1":
        return (
            "VERIFIED từ ma trận Ngô Gia Tự: 12 nhiều lựa chọn (3 đ; 7 nhận biết, 5 thông hiểu), 3 đúng/sai = 12 ý (3 đ; 6 nhận biết, "
            "3 thông hiểu, 3 vận dụng), 4 trả lời ngắn (2 đ; 1 nhận biết, 3 thông hiểu), 3 tự luận (2 đ). Tỉ lệ điểm 30/30/20/20. "
            "Phân bố theo chương (câu): 11C1 = 4 nhiều lựa chọn, 2 đúng/sai, 2 trả lời ngắn, 1 tự luận; 11C2 = 4 nhiều lựa chọn, "
            "1 đúng/sai, 1 trả lời ngắn, 1 tự luận; 11C3 = 4 nhiều lựa chọn, 0 đúng/sai, 1 trả lời ngắn, 1 tự luận."
        )
    return (
        f"(tự ước tính) Chưa tìm được ma trận {EXAM_LABEL[exam]} lớp {grade} đọc được. Cấu trúc 12 nhiều lựa chọn (3 đ) + "
        "3 đúng/sai (3 đ) + 4 trả lời ngắn (2 đ) + 3 tự luận (2 đ) lấy theo ma trận GK1 Toán 11 của THPT Ngô Gia Tự "
        "(mỗi trường ra một cấu trúc khác). Phạm vi chương theo phân phối chương sách Kết nối tri thức. "
        "Admin cần đối chiếu với ma trận của trường trước khi duyệt."
    )


def _semester_templates() -> list[dict]:
    rows = []
    for grade in (10, 11, 12):
        for exam in ("GK1", "CK1", "GK2", "CK2"):
            sections = _semester_sections(grade, exam)
            if grade == 12:
                source = SRC_G12
            elif grade == 11 and exam == "GK1":
                source = SRC_NGT
            else:
                source = (
                    "(tự ước tính) Cấu trúc theo ma trận GK1 Toán 11 Ngô Gia Tự 2025-2026 "
                    "(https://thpt-ngogiatu-daklak.edu.vn/wp-content/uploads/2025/10/Ma-tran-GK1-Toan-11-nam-2025-2026.docx), "
                    "phạm vi chương theo phân phối chương sách Kết nối tri thức. Chưa có ma trận chính thức của Bộ."
                )
            rows.append(
                {
                    "name": f"Toán {grade} – {EXAM_LABEL[exam]} ({YEAR})",
                    "exam_type": exam,
                    "grade": grade,
                    "version_label": YEAR,
                    "duration_minutes": 90,
                    "source": source,
                    "description": _semester_description(grade, exam),
                    "sections": sections,
                }
            )
    return rows


def templates() -> list[dict]:
    """Toàn bộ mẫu do migration này nạp, kèm trạng thái."""
    out = [dict(t, status="APPROVED") for t in (THPT_2025, THPT_2026)]
    out += [dict(t, status="DRAFT") for t in _semester_templates()]
    for t in out:
        t["total_questions"] = sum(s["count"] for s in t["sections"])
    return out


INSERT = sa.text(
    """
    INSERT INTO exam_templates
        (name, exam_type, grade, version_label, duration_minutes, source, description,
         sections, total_questions, status, approved_at)
    SELECT CAST(:name AS varchar), CAST(:exam_type AS varchar), CAST(:grade AS smallint),
           CAST(:version_label AS varchar), CAST(:duration_minutes AS integer), CAST(:source AS text),
           CAST(:description AS text), CAST(:sections AS jsonb), CAST(:total_questions AS integer),
           CAST(:status AS varchar), CASE WHEN CAST(:status AS varchar) = 'APPROVED' THEN now() END
    WHERE NOT EXISTS (
        SELECT 1 FROM exam_templates
        WHERE name = CAST(:name AS varchar) AND exam_type = CAST(:exam_type AS varchar)
          AND version_label = CAST(:version_label AS varchar)
    )
    """
)
DELETE = sa.text(
    "DELETE FROM exam_templates WHERE name = :name AND exam_type = :exam_type AND version_label = :version_label"
)


def upgrade() -> None:
    bind = op.get_bind()
    for t in templates():
        bind.execute(INSERT, {**t, "sections": json.dumps(t["sections"], ensure_ascii=False)})


def downgrade() -> None:
    bind = op.get_bind()
    for t in templates():
        bind.execute(DELETE, {"name": t["name"], "exam_type": t["exam_type"], "version_label": t["version_label"]})
