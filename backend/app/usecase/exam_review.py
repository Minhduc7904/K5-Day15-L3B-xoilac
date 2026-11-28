"""Chính sách chọn câu theo lịch sử làm bài của học sinh: tránh câu đã làm, hoặc ôn lại câu đã sai.

Hàm thuần trên `QuestionRecord` (kết quả từng câu qua các lượt đã chấm), không biết HTTP hay DB.

- Tránh trùng (`avoid_repeats`, mặc định của luồng "ôn tiếp"): loại mọi câu học sinh đã làm.
- Ôn lại câu sai (`review_wrong`): chỉ lấy câu học sinh từng sai; câu sai nhiều lần lấy trước, cùng số lần sai thì
  ngẫu nhiên. Cố ý trùng câu cũ, nên không loại câu đã làm.
"""
from collections import Counter
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field

from app.service.exam_chat_sources import QuestionRecord
from app.usecase.exam_preview_rules import (
    DEFAULT_POINT_WEIGHTS,
    MAX_TOTAL,
    MatrixCell,
    PreviewEdit,
    PreviewStructure,
    new_structure,
)

NO_WRONG = ("Mình chưa thấy câu nào em làm sai trong các bài đã chấm, nên chưa có gì để ôn lại. "
            "Em làm thêm một bài, hoặc chọn chương muốn ôn nhé.")
NOT_IN_BANK = ("Các câu em từng sai hiện không còn trong ngân hàng hoặc không thuộc phạm vi em chọn, "
               "nên mình không dựng đề ôn lại. Em đổi phạm vi hoặc chọn chương khác nhé.")


@dataclass(frozen=True)
class PickPolicy:
    """Ràng buộc thêm khi chọn câu: `avoid` là câu không được lấy, `only` giới hạn trong một tập câu,
    `priority` đẩy câu điểm cao lên trước. Mặc định là không ràng buộc (hành vi cũ)."""

    avoid: frozenset[int] = frozenset()
    only: frozenset[int] | None = None
    priority: Mapping[int, float] = field(default_factory=dict)

    @classmethod
    def for_structure(cls, structure: PreviewStructure, records: Mapping[int, QuestionRecord]) -> "PickPolicy":
        if structure.review_wrong:
            wrong = {qid: record.wrong for qid, record in records.items() if record.wrong > 0}
            return cls(only=frozenset(wrong), priority=wrong)
        if structure.avoid_repeats:
            return cls(avoid=frozenset(qid for qid, record in records.items() if record.done > 0))
        return cls()

    def picks(self) -> dict:
        """Tham số `only`, `priority` truyền cho `QuestionBankRepository.pick*`."""
        return {"only": self.only, "priority": self.priority or None}

    @property
    def active(self) -> bool:
        return bool(self.avoid) or self.only is not None


NO_POLICY = PickPolicy()   # không ràng buộc: hành vi chọn câu cũ


def rank_wrong(records: Iterable[QuestionRecord]) -> list[QuestionRecord]:
    """Câu từng sai, sai nhiều lần trước; bằng nhau thì sai gần đây trước, rồi mã câu."""
    wrong = [record for record in records if record.wrong > 0]
    return sorted(wrong, key=lambda r: (-r.wrong, -(r.last_wrong_at.timestamp() if r.last_wrong_at else 0), r.question_id))


def wrong_structure(
    ranked: list[QuestionRecord], cells: Mapping[int, tuple[str, str, str]], total: int | None,
) -> tuple[PreviewStructure | None, list[QuestionRecord], str | None]:
    """Dựng cấu trúc đề ôn lại câu sai từ danh sách đã xếp hạng.

    `cells`: mã câu khả dụng trong phạm vi → (chương, mức khó, loại câu). Lấy tối đa `total` câu đầu danh sách còn trong
    kho; ít hơn thì đề ngắn lại (không bù bằng câu chưa từng sai). Trả (cấu trúc, câu được chọn, lỗi)."""
    usable = [r for r in ranked if r.question_id in cells and cells[r.question_id][2] in DEFAULT_POINT_WEIGHTS]
    if not ranked:
        return None, [], NO_WRONG
    if not usable:
        return None, [], NOT_IN_BANK
    chosen = usable[: max(1, min(total or 10, MAX_TOTAL))]
    counts = Counter(cells[r.question_id] for r in chosen)
    rows = [MatrixCell(chapter=chapter, difficulty=difficulty, type=kind, count=count)
            for (chapter, difficulty, kind), count in counts.items()]
    per_chapter = Counter()
    for row in rows:
        per_chapter[row.chapter] += row.count
    structure = new_structure(dict(per_chapter), PreviewEdit(rows=rows))
    return structure.model_copy(update={"review_wrong": True}), chosen, None


def wrong_reason(chosen: Collection[QuestionRecord], requested: int | None) -> str:
    most = max(r.wrong for r in chosen)
    reason = f"Lý do: lấy {len(chosen)} câu em từng làm sai, câu sai nhiều lần xếp trước (nhiều nhất sai {most} lần)."
    if requested and requested > len(chosen):
        reason += f" Em chỉ có {len(chosen)} câu đã sai trong phạm vi này nên đề ngắn hơn {requested} câu em yêu cầu."
    return reason
