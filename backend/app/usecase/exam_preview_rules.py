"""Luật của bản xem trước đề ôn (issue #4). Hàm thuần: không biết HTTP, DB hay model.

Cả hai đường chỉnh (học sinh nhắn chat, frontend gọi API) đều đi qua apply_edit() rồi check_structure(), nên
cùng một quy tắc kiểm tra. Hành vi bám theo codebase/agent.py (lát cắt đã đo): chia câu theo trọng số độ khó bằng
phương pháp phần dư lớn nhất, mặc định 10 câu, trộn 20% NB · 40% TH · 40% VD, không lấy VDC.
"""
import re
from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["NB", "TH", "VD", "VDC"]
PreviewStatus = Literal["PROPOSED", "EDITED", "CONFIRMED", "BUILT"]

DIFFICULTIES: tuple[str, ...] = ("NB", "TH", "VD", "VDC")
DIFF_NAME = {"NB": "nhận biết", "TH": "thông hiểu", "VD": "vận dụng", "VDC": "vận dụng cao"}
DEFAULT_WEIGHTS: dict[str, float] = {"NB": 0.2, "TH": 0.4, "VD": 0.4}
DEFAULT_TOTAL = 10
MAX_TOTAL = 50
MAX_CHAPTERS = 5
CHAPTER_CODE = re.compile(r"^1[0-2]C\d+$")


class ChapterCount(BaseModel):
    code: str = Field(pattern=r"^1[0-2]C\d+$")
    count: int = Field(ge=1, le=MAX_TOTAL)


class PreviewStructure(BaseModel):
    """Cấu trúc đề học sinh đang xem: chương và số câu mỗi chương, cách trộn độ khó."""

    chapters: list[ChapterCount] = Field(min_length=1, max_length=MAX_CHAPTERS)
    difficulty_weights: dict[Difficulty, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    excluded_difficulties: list[Difficulty] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(c.count for c in self.chapters)

    def effective_weights(self) -> dict[str, float]:
        return {d: w for d, w in self.difficulty_weights.items() if w > 0 and d not in self.excluded_difficulties}


class PreviewEdit(BaseModel):
    """Một lần chỉnh. Trường None là giữ nguyên. Dùng chung cho chat và API."""

    total: int | None = Field(default=None, ge=1, le=MAX_TOTAL)
    chapter_codes: list[str] | None = Field(default=None, min_length=1, max_length=MAX_CHAPTERS)
    chapter_counts: dict[str, int] | None = None
    only_difficulty: Difficulty | None = None
    exclude_difficulties: list[Difficulty] | None = None
    difficulty_counts: dict[Difficulty, int] | None = None

    def is_empty(self) -> bool:
        return all(v is None for v in self.model_dump().values())


class PreviewRuleError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def allocate(n: int, weights: dict[str, float]) -> dict[str, int]:
    """Chia n câu theo trọng số (phương pháp phần dư lớn nhất), giữ thứ tự khoá. Giống codebase/agent.py."""
    total = sum(w for w in weights.values() if w > 0)
    if n <= 0 or total <= 0:
        return {}
    raw = {k: n * w / total for k, w in weights.items() if w > 0}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: n - sum(out.values())]:
        out[k] += 1
    return {k: v for k, v in out.items() if v}


def difficulty_plan(structure: PreviewStructure) -> dict[str, dict[str, int]]:
    """Số câu cần lấy theo từng chương và từng mức độ khó."""
    weights = structure.effective_weights()
    return {c.code: allocate(c.count, weights) for c in structure.chapters}


def check_structure(structure: PreviewStructure, known_chapters: set[str] | None = None) -> list[str]:
    """Trả danh sách lỗi (rỗng là hợp lệ). known_chapters: mã chương có trong danh mục, None là bỏ qua bước này."""
    errors: list[str] = []
    codes = [c.code for c in structure.chapters]
    if len(codes) != len(set(codes)):
        errors.append("Một chương bị lặp lại trong cấu trúc.")
    if structure.total > MAX_TOTAL:
        errors.append(f"Tổng {structure.total} câu vượt giới hạn {MAX_TOTAL} câu của một đề ôn.")
    if any(w < 0 for w in structure.difficulty_weights.values()):
        errors.append("Trọng số độ khó không được âm.")
    if not structure.effective_weights():
        errors.append("Không còn mức độ khó nào để chọn câu (đã loại hết).")
    if known_chapters is not None:
        unknown = [c for c in codes if c not in known_chapters]
        if unknown:
            errors.append("Chưa có chương %s trong danh mục." % ", ".join(unknown))
    return errors


def ensure_valid(structure: PreviewStructure, known_chapters: set[str] | None = None) -> None:
    errors = check_structure(structure, known_chapters)
    if errors:
        raise PreviewRuleError(errors)


def new_structure(chapter_counts: dict[str, int], edit: PreviewEdit | None = None) -> PreviewStructure:
    base = PreviewStructure(chapters=[ChapterCount(code=c, count=n) for c, n in chapter_counts.items()])
    return apply_edit(base, edit) if edit and not edit.is_empty() else base


def apply_edit(structure: PreviewStructure, edit: PreviewEdit) -> PreviewStructure:
    """Áp một lần chỉnh, trả cấu trúc mới (không sửa bản cũ). Chưa kiểm hợp lệ: gọi ensure_valid() sau."""
    s = structure.model_copy(deep=True)
    total = edit.total if edit.total is not None else s.total

    if edit.chapter_counts:
        s.chapters = [ChapterCount(code=c, count=n) for c, n in edit.chapter_counts.items()]
    elif edit.chapter_codes:
        counts = allocate(total, {c: 1.0 for c in dict.fromkeys(edit.chapter_codes)})
        s.chapters = [ChapterCount(code=c, count=n) for c, n in counts.items()]
    elif edit.total is not None and edit.total != s.total:
        # Giữ tỉ lệ giữa các chương hiện có.
        counts = allocate(edit.total, {c.code: float(c.count) for c in s.chapters})
        s.chapters = [ChapterCount(code=c, count=n) for c, n in counts.items()]

    if edit.difficulty_counts:
        s.difficulty_weights = {d: float(k) for d, k in edit.difficulty_counts.items() if k > 0}
        s.excluded_difficulties = [d for d in s.excluded_difficulties if d not in s.difficulty_weights]
    if edit.only_difficulty:
        s.difficulty_weights = {edit.only_difficulty: 1.0}
        s.excluded_difficulties = []
    if edit.exclude_difficulties:
        s.excluded_difficulties = sorted(set(s.excluded_difficulties) | set(edit.exclude_difficulties),
                                         key=DIFFICULTIES.index)
    return s


def next_status_after_edit(status: str) -> str:
    """Mọi lần chỉnh đưa bản xem trước về EDITED; bản đã xác nhận hay đã dựng phải xác nhận lại."""
    return "EDITED"


def can_confirm(status: str) -> bool:
    return status in ("PROPOSED", "EDITED")


def describe(structure: PreviewStructure, chapter_names: dict[str, str] | None = None) -> str:
    """Mô tả cấu trúc bằng lời cho tin nhắn của agent."""
    names = chapter_names or {}
    plan = difficulty_plan(structure)
    lines = []
    for c in structure.chapters:
        mix = ", ".join("%d %s" % (k, DIFF_NAME[d]) for d, k in plan[c.code].items())
        label = f"{c.code} {names[c.code]}" if names.get(c.code) else c.code
        lines.append(f"- {label}: {c.count} câu ({mix})")
    if structure.excluded_difficulties:
        lines.append("Đã bỏ mức: %s." % ", ".join(DIFF_NAME[d] for d in structure.excluded_difficulties))
    return "\n".join(lines)
