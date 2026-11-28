"""Match plain text (OCR of a student's exercise image) to catalog chapters by chapter name."""
import math
import re
import unicodedata
from collections import Counter

STOP = {"trong", "cua", "va", "cac", "mot", "hai", "de", "ve", "theo", "so", "tu", "den", "tren", "voi", "la", "co"}
# Notation that names a chapter without spelling its title (kept short: the catalog names do the rest).
NOTATION = (
    (re.compile(r"oxyz"), "he truc toa do khong gian vecto"),
    (re.compile(r"oxy(?!z)"), "toa do mat phang"),
    (re.compile(r"\b(?:sin|cos|tan|cot)\b"), "luong giac"),
    (re.compile(r"\b(?:log|ln)\b"), "logarit"),
    (re.compile(r"\blim\b"), "gioi han"),
)
MIN_SCORE = 1.0
CLEAR_LEAD = 1.5


def fold(text: str) -> str:
    plain = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    plain = "".join(ch for ch in plain if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def _terms(name: str) -> set[str]:
    """Name keywords plus adjacent-word phrases, so "mat phang" counts but "hinh lap phuong" does not hit "phuong"."""
    words = [word for word in fold(name).split() if word not in STOP and len(word) > 1]
    return set(words) | {" ".join(words[i:i + n]) for n in (2, 3) for i in range(len(words) - n + 1)}


def chapter_hints(text: str, catalog: dict[str, dict], limit: int = 3) -> list[dict]:
    """Rank parent chapters by how often their (and their children's) name terms appear in `text`.

    Returns [{"code", "name", "score", "leaves": [leaf codes that matched]}], best first; empty when nothing matches.
    """
    folded = fold(text)
    compact = folded.replace(" ", "")
    extra = " ".join(words for pattern, words in NOTATION if pattern.search(folded) or pattern.search(compact))
    padded = f" {folded} {' '.join([extra] * 3)} "
    names = {code: _terms(entry["name"]) for code, entry in catalog.items()}
    spread = Counter(term for terms in names.values() for term in terms)
    scores: dict[str, list[float]] = {}
    matched: dict[str, list[str]] = {}
    for code, entry in catalog.items():
        total = 0.0
        for term in names[code]:
            seen = padded.count(f" {term} ")
            if seen:
                total += math.log(1 + len(names) / spread[term]) * (1 + math.log(seen)) * (1 + term.count(" ") ** 2)
        if not total:
            continue
        parent = entry.get("parent_code") or code
        scores.setdefault(parent, []).append(total / math.sqrt(len(names[code])))
        if entry.get("parent_code"):
            matched.setdefault(parent, []).append(code)
    totals = {code: max(parts) + 0.25 * (sum(parts) - max(parts)) for code, parts in scores.items()}
    ranked = sorted((item for item in totals.items() if item[1] >= MIN_SCORE), key=lambda item: -item[1])
    return [{"code": code, "name": catalog[code]["name"], "score": round(score, 2), "leaves": matched.get(code, [])}
            for code, score in ranked[:limit] if code in catalog]


def clear_winner(hints: list[dict]) -> dict | None:
    """The top hint when it clearly beats the runner-up, else None."""
    if not hints:
        return None
    if len(hints) == 1 or hints[0]["score"] >= CLEAR_LEAD * hints[1]["score"]:
        return hints[0]
    return None


LEVEL_NAME = {"NB": "nhận biết", "TH": "thông hiểu", "VD": "vận dụng", "VDC": "vận dụng cao"}
TYPE_NAME = {"SINGLE_CHOICE": "trắc nghiệm", "TRUE_FALSE": "đúng/sai", "SHORT_ANSWER": "trả lời ngắn"}


def matrix_rows(tags) -> list[dict]:
    """Group per-question tags into matrix cells (chapter x level x type), keeping first-seen order."""
    cells = Counter((tag.chapter_code, tag.difficulty, tag.type) for tag in tags)
    return [{"chapter": chapter, "difficulty": level, "type": kind, "count": count}
            for (chapter, level, kind), count in cells.items()]


def scale_rows(rows: list[dict], total: int) -> list[dict]:
    """Keep the picture's proportions but make the exam `total` questions (largest-remainder split)."""
    size = sum(row["count"] for row in rows)
    if not rows or total == size:
        return rows
    raw = [total * row["count"] / size for row in rows]
    counts = [int(value) for value in raw]
    for index in sorted(range(len(rows)), key=lambda i: raw[i] - counts[i], reverse=True)[: total - sum(counts)]:
        counts[index] += 1
    return [{**row, "count": count} for row, count in zip(rows, counts) if count]


def describe_rows(rows: list[dict], catalog: dict[str, dict]) -> str:
    """Plain-language matrix for the agent's reply: totals first, then one line per chapter."""
    total = sum(row["count"] for row in rows)
    by_type = Counter()
    by_level = Counter()
    by_chapter: dict[str, list[dict]] = {}
    for row in rows:
        by_type[row["type"]] += row["count"]
        by_level[row["difficulty"]] += row["count"]
        by_chapter.setdefault(row["chapter"], []).append(row)
    lines = [f"Ma trận đề rút ra từ ảnh ({total} câu):",
             "- Dạng câu: " + ", ".join(f"{n} {TYPE_NAME[k]}" for k, n in by_type.items()),
             "- Mức độ: " + ", ".join(f"{by_level[k]} {LEVEL_NAME[k]}" for k in LEVEL_NAME if by_level[k])]
    for code, cells in by_chapter.items():
        name = catalog.get(code, {}).get("name", code)
        detail = ", ".join(f"{c['count']} {LEVEL_NAME[c['difficulty']]} {TYPE_NAME[c['type']]}" for c in cells)
        lines.append(f"- {code} {name}: {sum(c['count'] for c in cells)} câu ({detail})")
    return chr(10).join(lines)
