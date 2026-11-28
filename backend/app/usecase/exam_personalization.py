"""Build and verify the evidence and matrix for a history-based exam."""
from collections import Counter
from dataclasses import dataclass

from app.service.exam_chat_model import ChatAction, PracticeRecommendation
from app.service.exam_chat_sources import HISTORY_ATTEMPTS, HISTORY_DAYS, MIN_ANSWERED, WEAK_ERROR_RATE, StudentHistory
from app.usecase.exam_chapter_scope import leaf_codes
from app.usecase.exam_preview_rules import (
    DEFAULT_TOTAL, DIFF_NAME, DIFFICULTIES, MAX_TOTAL, MatrixCell, PreviewEdit, PreviewRuleError, new_structure,
)

TYPE_NAMES = {"SINGLE_CHOICE": "trắc nghiệm", "TRUE_FALSE": "đúng/sai", "SHORT_ANSWER": "trả lời ngắn"}
RATIONALES = {
    "reinforce_basics": "Củng cố kiến thức nền",
    "practice_application": "Luyện vận dụng",
    "assess_coverage": "Luyện để có thêm dữ liệu",
    "balanced_review": "Ôn lại kiến thức",
}
CLOSE_GAP = 0.10
INVALID = "Mình chưa ghép được cấu trúc khớp lịch sử và yêu cầu. Em thử lại hoặc chọn chương muốn ôn nhé."


@dataclass(frozen=True)
class PracticeRequest:
    action: ChatAction
    total: int
    scope: list[str]
    difficulties: list[str]
    types: list[str]

    @classmethod
    def from_action(cls, action, catalog):
        counts = action.chapter_counts
        scope = list(dict.fromkeys([*action.chapters, *counts]))
        if set(scope) - catalog.keys():
            raise PreviewRuleError(["Em chọn chương có trong danh mục nhé."])
        difficulty_counts = action.difficulty_counts
        total = (action.total or sum(counts.values()) or sum(action.type_counts.values())
                 or sum(difficulty_counts.values()) or DEFAULT_TOTAL)
        types = list(action.type_counts or ["SINGLE_CHOICE"])
        if (not 1 <= total <= MAX_TOTAL or sum(counts.values()) > total
                or sum(difficulty_counts.values()) > total or set(types) - TYPE_NAMES.keys()
                or action.type_counts and sum(action.type_counts.values()) != total):
            raise PreviewRuleError(["Em kiểm tra lại tổng số câu, dạng câu và mức độ muốn luyện nhé."])
        full_mix = sum(difficulty_counts.values()) == total
        difficulties = [key for key in DIFFICULTIES if difficulty_counts.get(key, 0 if full_mix else 1) > 0
                        and (key != "VDC" or difficulty_counts.get(key, 0) > 0)]
        return cls(action, total, scope, difficulties, types)

    def parameters(self):
        return {
            "total": self.total, "selected_chapters": self.scope,
            "chapter_counts": self.action.chapter_counts,
            "difficulty_counts": self.action.difficulty_counts, "type_counts": self.action.type_counts,
        }


def review_text(history: StudentHistory | None, catalog: dict) -> str:
    if history is None:
        return "Em chưa có lịch sử làm bài đã chấm."
    if not history.attempt_count:
        return f"Em chưa có lượt làm bài đã chấm trong {HISTORY_DAYS} ngày qua."
    lines = [f"Mình xem {history.attempt_count} lượt đã chấm gần nhất trong {HISTORY_DAYS} ngày "
             f"(tối đa {HISTORY_ATTEMPTS} lượt)."]
    for title, rows in (("Bài vừa làm", history.latest), ("Các bài trước đó", history.earlier)):
        parts = []
        for row in rows:
            if row.total or row.skipped:
                outcome = f"sai {row.incorrect}/{row.total} câu đã làm" if row.total else "chưa làm câu nào"
                skipped = f", bỏ qua {row.skipped}" if row.skipped else ""
                parts.append(f"{catalog[row.code]['name']}: {outcome}{skipped}")
        if parts:
            lines.append(f"{title}: " + "; ".join(parts) + ".")
    if history.incomplete:
        lines.append(f"Có {history.incomplete} mục thiếu kết quả hoặc nhãn chương rõ ràng.")
    if history.conflicting:
        lines.append("Có kết quả mâu thuẫn trong cùng lượt làm.")
    low_evidence = [catalog[row.code]["name"] for row in history.chapters if row.classification == "under_practiced"]
    if low_evidence:
        lines.append(f"Còn ít dữ liệu (dưới {MIN_ANSWERED} câu đã làm): " + ", ".join(low_evidence) + ".")
    unseen = [catalog[row.code]["name"] for row in history.chapters if row.classification == "unpracticed"]
    if unseen:
        lines.append("Chưa luyện trong giai đoạn này: " + ", ".join(unseen) + ".")
    return "\n".join(lines)


def practice_chapters(history, request, catalog):
    parents = {code: item["parent_code"] for code, item in catalog.items()}
    scope = request.scope or [row.code for row in history.chapters]
    return list(dict.fromkeys(leaf for code in scope for leaf in leaf_codes(code, parents)))


def weak_priority(history, options, catalog):
    available = {catalog[cell["chapter_code"]]["parent_code"] or cell["chapter_code"] for cell in options}
    ranked = sorted(
        (row for row in history.chapters if row.classification == "weak" and row.code in available),
        key=lambda row: (-row.error_rate, row.code),
    )
    if len(ranked) >= 2 and ranked[0].error_rate - ranked[1].error_rate <= CLOSE_GAP + 1e-9:
        return [row.code for row in ranked[:2]]
    return [row.code for row in ranked[:1]]


def rationale_for(status, difficulty):
    if status == "weak":
        return "reinforce_basics" if difficulty in {"NB", "TH"} else "practice_application"
    return "balanced_review" if status == "adequate" else "assess_coverage"


def recommendation_context(history, request, catalog, options, priority):
    cohorts = [{row.code: row for row in rows} for rows in (history.latest, history.earlier)]
    evidence = {row.code: row for row in history.chapters}
    bank = []
    for cell in options:
        chapter = cell["chapter_code"]
        root = catalog[chapter]["parent_code"] or chapter
        # A required weak chapter fills the last slot when the requested exam is that short.
        if priority and not request.action.chapter_counts and request.total <= len(priority):
            if root not in priority[:request.total]:
                continue
        bank.append({**cell, "evidence_ref": root,
                     "rationale": rationale_for(evidence[root].classification, cell["difficulty"])})

    def counts(row):
        return {"attempted": row.total, "correct": row.correct, "incorrect": row.incorrect,
                "skipped": row.skipped, "error_rate": row.error_rate}

    return {
        **request.parameters(), "grade": request.action.grade, "history_days": HISTORY_DAYS,
        "max_attempts": HISTORY_ATTEMPTS, "attempt_count": history.attempt_count,
        "min_answered": MIN_ANSWERED, "weak_error_rate": WEAK_ERROR_RATE, "incomplete": history.incomplete,
        "weak_priority": priority,
        "bank": bank,
        "evidence": {row.code: {"name": catalog[row.code]["name"], "status": row.classification,
                                "recent": counts(row), "latest": counts(cohorts[0][row.code]),
                                "earlier": counts(cohorts[1][row.code])} for row in history.chapters},
    }


def validate_recommendation(
    recommendation: PracticeRecommendation, history, request, catalog, options, priority,
):
    capacity = {(c["chapter_code"], c["difficulty"], c["type"]): c["available"] for c in options}
    evidence = {row.code: row for row in history.chapters}
    root_counts, chapter_counts, difficulty_counts, type_counts = Counter(), Counter(), Counter(), Counter()
    rows = []
    reasons = []
    for group in recommendation.groups:
        key = (group.chapter_code, group.difficulty, group.type)
        if key not in capacity or group.count > capacity.pop(key):
            raise PreviewRuleError(["Đề xuất có ô vượt số câu hiện có trong kho."])
        root = catalog[group.chapter_code]["parent_code"] or group.chapter_code
        row = evidence.get(root)
        if (group.evidence_ref != root or row is None
                or group.rationale != rationale_for(row.classification, group.difficulty)):
            raise PreviewRuleError([INVALID])
        root_counts[root] += group.count
        chapter_counts[group.chapter_code] += group.count
        difficulty_counts[group.difficulty] += group.count
        type_counts[group.type] += group.count
        rows.append(MatrixCell(chapter=group.chapter_code, difficulty=group.difficulty, type=group.type, count=group.count))
        fact = (f"sai {row.incorrect}/{row.total} câu đã làm" if row.total else "chưa làm câu nào trong giai đoạn này")
        if row.classification == "under_practiced":
            fact += ", còn ít dữ liệu"
        name = catalog[group.chapter_code]["name"]
        reason = RATIONALES[group.rationale]
        reasons.append(f"- {name}, {group.count} câu {DIFF_NAME[group.difficulty]}: {reason.lower()} ({fact}).")
    action = request.action
    if (sum(type_counts.values()) != request.total
            or any((root_counts if not catalog[code]["parent_code"] else chapter_counts)[code] != count
                   for code, count in action.chapter_counts.items())
            or any(difficulty_counts[code] != count for code, count in action.difficulty_counts.items())
            or any(type_counts[code] != count for code, count in action.type_counts.items())):
        raise PreviewRuleError([INVALID])
    if priority and not action.chapter_counts:
        first, *other = priority
        if not root_counts[first] or (other and request.total >= 2
                                     and not 0 < root_counts[other[0]] <= root_counts[first]):
            raise PreviewRuleError([INVALID])
    return new_structure(dict(chapter_counts), PreviewEdit(rows=rows, duration_minutes=action.duration_minutes)), reasons
