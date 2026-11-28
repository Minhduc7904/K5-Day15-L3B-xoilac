"""Bản xem trước theo mẫu kỳ thi (issue #4, nhánh "ôn theo mẫu kỳ thi"). Hàm thuần: không biết HTTP, DB hay model.

Nguồn: một mẫu cấu trúc đề ĐÃ DUYỆT từ issue #5 (hợp đồng GET /exam-templates/lookup, xem
docs/api/exam-templates-api.md trên nhánh #5). Mẫu cố định các phần, loại câu, số câu và phân bố độ khó, nên
học sinh chỉ được THU HẸP phạm vi chương trong giới hạn mẫu cho phép. Mọi chỉnh sửa khác (đổi số câu, đổi độ khó,
thêm chương ngoài mẫu) là xung đột với ràng buộc của mẫu và bị từ chối kèm lý do, cùng một luật cho chat và API.
"""
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.usecase.exam_preview_rules import DIFF_NAME, Difficulty, PreviewEdit, PreviewRuleError

QuestionType = Literal["SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE", "SHORT_ANSWER", "ESSAY"]
TYPE_NAME = {
    "SINGLE_CHOICE": "trắc nghiệm một đáp án",
    "MULTIPLE_CHOICE": "trắc nghiệm nhiều đáp án",
    "TRUE_FALSE": "đúng/sai",
    "SHORT_ANSWER": "trả lời ngắn",
    "ESSAY": "tự luận",
}
EXAM_NAME = {
    "GK1": "giữa học kỳ 1", "GK2": "giữa học kỳ 2", "CK1": "cuối học kỳ 1", "CK2": "cuối học kỳ 2",
    "THPT": "tốt nghiệp THPT", "HSA": "đánh giá năng lực HSA", "TSA": "đánh giá tư duy TSA",
}
CHAPTER_GRADE = re.compile(r"^(1[0-2])C\d+$")


class TemplateSectionPlan(BaseModel):
    order: int
    title: str
    question_type: QuestionType
    count: int = Field(ge=1)
    points_per_question: float | None = None
    difficulty_distribution: dict[Difficulty, int] | None = None
    allowed_chapters: list[str] | None = None   # chương mẫu cho phép; None là mẫu không giới hạn chương
    chapters: list[str] | None = None           # chương học sinh đang chọn (tập con của allowed_chapters)

    def effective_chapters(self) -> list[str] | None:
        return self.chapters if self.chapters else self.allowed_chapters

    def difficulty_plan(self) -> dict[str | None, int]:
        """Số câu theo mức độ khó. Mẫu không quy định phân bố thì lấy mọi mức (khoá None)."""
        if self.difficulty_distribution:
            return {d: k for d, k in self.difficulty_distribution.items() if k > 0}
        return {None: self.count}


class TemplatePreviewStructure(BaseModel):
    """Cấu trúc đề theo một mẫu đã duyệt. Lưu bản chụp của mẫu để đề dựng ra khớp đúng mẫu lúc học sinh xác nhận."""

    kind: Literal["EXAM_TEMPLATE"] = "EXAM_TEMPLATE"
    template_id: int
    template_name: str
    exam_type: str
    grade: int | None = None
    version_label: str | None = None
    duration_minutes: int | None = None
    source: str | None = None
    sections: list[TemplateSectionPlan] = Field(min_length=1)

    @property
    def total(self) -> int:
        return sum(s.count for s in self.sections)


class TemplateConflict(PreviewRuleError):
    """Chỉnh sửa vi phạm ràng buộc của mẫu kỳ thi. errors là lý do đọc được cho học sinh."""


def from_template(template: dict[str, Any]) -> TemplatePreviewStructure:
    """Dựng bản xem trước từ một mẫu theo hợp đồng #5 (dict có các khoá của ExamTemplateOut)."""
    sections = [
        TemplateSectionPlan(
            order=s["order"],
            title=s["title"],
            question_type=s["question_type"],
            count=s["count"],
            points_per_question=s.get("points_per_question"),
            difficulty_distribution=s.get("difficulty_distribution"),
            allowed_chapters=list(s["chapter_codes"]) if s.get("chapter_codes") else None,
        )
        for s in sorted(template["sections"], key=lambda s: s["order"])
    ]
    return TemplatePreviewStructure(
        template_id=template["template_id"],
        template_name=template["name"],
        exam_type=template["exam_type"],
        grade=template.get("grade"),
        version_label=template.get("version_label"),
        duration_minutes=template.get("duration_minutes"),
        source=template.get("source"),
        sections=sections,
    )


def _edit_fields(edit: PreviewEdit) -> set[str]:
    return {k for k, v in edit.model_dump().items() if v is not None}


def apply_template_edit(structure: TemplatePreviewStructure, edit: PreviewEdit) -> TemplatePreviewStructure:
    """Áp chỉnh sửa lên bản xem trước theo mẫu. Chỉ cho thu hẹp chương; còn lại báo TemplateConflict."""
    errors: list[str] = []
    fields = _edit_fields(edit)
    if "total" in fields and edit.total != structure.total:
        errors.append(f"Mẫu \"{structure.template_name}\" cố định {structure.total} câu, không đổi được số câu.")
    if fields & {"only_difficulty", "exclude_difficulties", "difficulty_counts"}:
        errors.append("Mẫu kỳ thi cố định phân bố độ khó, không đổi được độ khó.")
    if "chapter_counts" in fields:
        errors.append("Mẫu kỳ thi cố định số câu từng phần, không chia lại số câu theo chương được.")
    if "type_point_weights" in fields:
        errors.append("Mẫu kỳ thi giữ nguyên quy tắc phân bổ điểm.")

    s = structure.model_copy(deep=True)
    if edit.chapter_codes:
        wanted = list(dict.fromkeys(edit.chapter_codes))
        for code in wanted:
            m = CHAPTER_GRADE.match(code)
            if structure.grade is not None and m and int(m.group(1)) > structure.grade:
                errors.append(f"Chương {code} thuộc lớp {m.group(1)}, vượt khối {structure.grade} của mẫu.")
        allowed_any = [c for sec in s.sections for c in (sec.allowed_chapters or [])]
        outside = [c for c in wanted if allowed_any and c not in allowed_any]
        if outside:
            errors.append("Chương %s không nằm trong phạm vi của mẫu (mẫu cho phép: %s)."
                          % (", ".join(outside), ", ".join(dict.fromkeys(allowed_any))))
        for sec in s.sections:
            if sec.allowed_chapters is None:
                sec.chapters = wanted
            else:
                picked = [c for c in wanted if c in sec.allowed_chapters]
                # Phần không giao với lựa chọn thì giữ phạm vi gốc của mẫu, để không làm rỗng phần đó.
                sec.chapters = picked or None

    if errors:
        raise TemplateConflict(errors)
    return s


def describe_template(structure: TemplatePreviewStructure, chapter_names: dict[str, str] | None = None) -> str:
    """Mô tả bản xem trước theo mẫu bằng lời cho tin nhắn của agent."""
    names = chapter_names or {}
    head = f"Mẫu \"{structure.template_name}\" ({EXAM_NAME.get(structure.exam_type, structure.exam_type)}"
    if structure.grade:
        head += f", lớp {structure.grade}"
    if structure.version_label:
        head += f", {structure.version_label}"
    head += f"): {structure.total} câu"
    if structure.duration_minutes:
        head += f", {structure.duration_minutes} phút"
    lines = [head + "."]
    for sec in structure.sections:
        plan = sec.difficulty_plan()
        mix = ", ".join(f"{k} {DIFF_NAME[d]}" for d, k in plan.items() if d) or "mọi mức độ khó"
        chapters = sec.effective_chapters()
        scope = ", ".join(f"{c} {names[c]}" if names.get(c) else c for c in chapters) if chapters else "mọi chương"
        lines.append(f"- {sec.title}: {sec.count} câu {TYPE_NAME[sec.question_type]} ({mix}); chương: {scope}")
    if structure.source:
        lines.append(f"Nguồn cấu trúc: {structure.source}.")
    return "\n".join(lines)
