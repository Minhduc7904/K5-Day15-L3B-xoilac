"""Luật nghiệp vụ của mẫu cấu trúc đề (issue #5). Hàm thuần, không biết HTTP hay DB, dễ test riêng.

Dùng chung cho tạo, sửa và duyệt. Issue #4 cũng gọi được để kiểm cấu trúc học sinh chỉnh so với mẫu.
"""
import re

from app.schemas.exam_template import ExamTemplateIn

MAX_TOTAL_QUESTIONS = 200
SEMESTER_EXAMS = {"GK1", "GK2", "CK1", "CK2"}   # giữa kỳ / cuối kỳ: gắn với một khối
NATIONAL_EXAMS = {"THPT", "HSA", "TSA"}          # thi tốt nghiệp, đánh giá năng lực: kiến thức lớp 10–12
CHAPTER_CODE = re.compile(r"^(1[0-2])C\d+$")     # mã chương như data/chapters.csv: 10C1, 12C43


class TemplateValidationError(Exception):
    """Mẫu vi phạm luật nghiệp vụ. errors là danh sách lý do, đọc được cho admin."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def total_questions(data: ExamTemplateIn) -> int:
    return sum(s.count for s in data.sections)


def check_template(data: ExamTemplateIn, *, for_approval: bool) -> list[str]:
    """Trả danh sách lỗi (rỗng là hợp lệ). for_approval=True thêm điều kiện bắt buộc để mẫu được duyệt."""
    errors: list[str] = []

    if data.exam_type in SEMESTER_EXAMS and data.grade is None:
        errors.append(f"Kỳ thi {data.exam_type} phải ghi khối lớp (10, 11 hoặc 12).")
    if data.exam_type in NATIONAL_EXAMS and data.grade not in (None, 12):
        errors.append(f"Kỳ thi {data.exam_type} chỉ áp dụng cho khối 12 (hoặc để trống).")

    orders = [s.order for s in data.sections]
    if len(orders) != len(set(orders)):
        errors.append("Thứ tự các phần (order) bị trùng.")

    total = total_questions(data)
    if total > MAX_TOTAL_QUESTIONS:
        errors.append(f"Tổng số câu {total} vượt giới hạn {MAX_TOTAL_QUESTIONS}.")

    for s in data.sections:
        where = f"Phần {s.order} ({s.title})"
        if s.difficulty_distribution is not None:
            if any(v < 0 for v in s.difficulty_distribution.values()):
                errors.append(f"{where}: số câu theo độ khó không được âm.")
            dist_sum = sum(s.difficulty_distribution.values())
            if dist_sum != s.count:
                errors.append(f"{where}: phân bố độ khó cộng lại {dist_sum} câu, khác số câu của phần là {s.count}.")
        for code in s.chapter_codes or []:
            m = CHAPTER_CODE.match(code)
            if not m:
                errors.append(f"{where}: mã chương '{code}' sai định dạng (ví dụ đúng: 12C1).")
                continue
            chapter_grade = int(m.group(1))
            if data.exam_type in SEMESTER_EXAMS and data.grade is not None and chapter_grade != data.grade:
                errors.append(f"{where}: chương {code} thuộc lớp {chapter_grade}, không thuộc khối {data.grade} của đề.")

    if for_approval and not (data.source or "").strip():
        errors.append("Phải ghi nguồn của cấu trúc (văn bản, đề minh hoạ…) trước khi duyệt.")

    return errors


def ensure_valid(data: ExamTemplateIn, *, for_approval: bool) -> None:
    errors = check_template(data, for_approval=for_approval)
    if errors:
        raise TemplateValidationError(errors)
