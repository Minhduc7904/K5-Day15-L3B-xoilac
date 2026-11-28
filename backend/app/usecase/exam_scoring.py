from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re

from app.usecase.exam_preview_rules import DEFAULT_POINT_WEIGHTS, PreviewRuleError
TRUE_FALSE_FACTORS = tuple(map(Fraction, ("0", "0.10", "0.25", "0.50", "1")))


def allocate_points(items: list[dict], structure: dict) -> list[dict]:
    if not items or any(item["type"] not in DEFAULT_POINT_WEIGHTS for item in items):
        raise PreviewRuleError(["Đề luyện tập cần có câu thuộc loại hỗ trợ chấm tự động."])
    sections = {section["order"]: section for section in structure.get("sections", [])}
    fixed = [
        sections.get(item.get("section_order"), {}).get("points_per_question") for item in items
    ]
    points = [Fraction(str(value)) if value is not None else None for value in fixed]
    fixed_total = sum(value for value in points if value is not None)
    missing = {}
    for item, value in zip(items, points):
        if value is None:
            kind = item["type"]
            missing[kind] = missing.get(kind, 0) + 1
    if missing and fixed_total >= 10:
        raise PreviewRuleError(["Điểm có sẵn phải nhỏ hơn 10 khi mẫu còn câu chưa có điểm."])
    weights = structure.get("type_point_weights") or DEFAULT_POINT_WEIGHTS
    weight_total = sum(weights.get(kind, 0) for kind in missing)
    if any(weights.get(kind, 0) <= 0 for kind in missing):
        raise PreviewRuleError(["Mỗi loại câu chưa có điểm cần trọng số dương."])
    result = []
    for item, value, original in zip(items, points, fixed):
        kind = item["type"]
        if value is None:
            score = (10 - fixed_total) * Fraction(weights[kind], weight_total * missing[kind])
        else:
            score = value if missing else value * 10 / fixed_total
        result.append({**item, "points": float(score) if original is None else original,
                       "max_points": float(score), "points_exact": str(score)})
    return result


def normalize_short(value: str) -> Decimal | str:
    text = " ".join(value.strip().split())
    candidate = text.translate(str.maketrans("−–—", "---")).replace(",", ".")
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", candidate):
        try:
            return Decimal(candidate)
        except InvalidOperation:
            pass
    return text


def grade_question(item: dict, key: dict, answer) -> tuple[Fraction, str, int | None]:
    maximum = Fraction(item["points_exact"])
    if item["type"] == "TRUE_FALSE":
        if not answer or all(value is None for value in answer):
            return Fraction(0), "skipped", 0
        count = sum(value is correct for value, correct in zip(answer, key["statements"]))
        status = "correct" if count == 4 else "partial" if count else "wrong"
        return maximum * TRUE_FALSE_FACTORS[count], status, count
    if not answer or not answer.strip():
        return Fraction(0), "skipped", None
    if item["type"] == "SINGLE_CHOICE":
        correct = answer == chr(65 + key["statements"].index(True))
    else:
        correct = normalize_short(answer) == normalize_short(key["answer"])
    return (maximum, "correct", None) if correct else (Fraction(0), "wrong", None)
