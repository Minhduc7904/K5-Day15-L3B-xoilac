import hashlib
import math
import re
from collections import defaultdict

from app.repositories.pdf_imports import PdfImportRepository
from app.service.pdf_import_models import PdfImportModels

REFERENCE_LIMIT = 160
MIN_SIMILARITY = 0.65
MIN_MARGIN = 0.12
TOP_K = 5
CHAPTER_CODE = re.compile(r"(10|11|12)C\d+")
MEDIA = re.compile(r"!\[[^\]]*\]\((?:media|media-missing):[^)]*\)")


def embedding_text(content: str, options: list[str]) -> str:
    text = "\n".join(" ".join(MEDIA.sub("", value).split()) for value in [content, *options])
    return text.strip()[:6000]


def unit_vector(vector: list[float]) -> list[float]:
    length = math.hypot(*vector)
    return [number / length for number in vector] if length else []


def vote(neighbors: list[dict], field: str) -> str | None:
    weights: dict[str, float] = defaultdict(float)
    for row in neighbors:
        label = row[field]
        if label:
            weights[label] += row["similarity"]
    ranked = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    if not ranked:
        return None
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    return ranked[0][0] if (ranked[0][1] - runner_up) / sum(weights.values()) >= MIN_MARGIN else None


def suggest(vector: list[float], references: list[tuple[dict, list[float]]]) -> dict:
    query = unit_vector(vector)
    neighbors = []
    for ref, reference in references:
        if len(query) != len(reference) or not query:
            continue
        score = max(-1.0, min(1.0, sum(left * right for left, right in zip(query, reference))))
        neighbors.append({
            "questionId": ref["question_id"], "chapter": ref["root_code"],
            "subchapter": ref["chapter_code"] if ref["chapter_code"] != ref["root_code"] else None,
            "difficulty": ref["difficulty"], "similarity": score,
        })
    neighbors.sort(key=lambda ref: (-ref["similarity"], ref["questionId"]))
    nearest = neighbors[:TOP_K]
    accepted = [row for row in nearest if row["similarity"] >= MIN_SIMILARITY]
    chapter = vote(accepted, "chapter")
    supporting = [row for row in accepted if row["chapter"] == chapter]
    subchapter = vote(supporting, "subchapter")
    return {
        "chapter": chapter, "subchapter": subchapter, "grade": int(chapter[:2]) if chapter else None,
        "difficulty": vote(accepted, "difficulty"), "neighbors": nearest,
    }


async def classify_drafts(drafts: list[dict], repo: PdfImportRepository, models: PdfImportModels) -> None:
    candidates = [
        draft for draft in drafts if not draft["imageDependent"]
    ]
    for draft in drafts:
        draft["suggestions"] = suggest([], [])
    if candidates:
        references = await load_references(repo, models)
        if references:
            pairs = [
                (draft, embedding_text(draft["content"], [item["content"] for item in draft["statements"]]))
                for draft in candidates
            ]
            pairs = [(draft, value) for draft, value in pairs if value]
            if pairs:
                vectors = await models.embed([value for _, value in pairs])
                for (draft, _), vector in zip(pairs, vectors, strict=True):
                    draft["suggestions"] = suggest(vector, references)
    for draft in drafts:
        if not all(draft["suggestions"][key] for key in ("chapter", "difficulty")):
            draft["flags"].append("label_review")


async def load_references(repo: PdfImportRepository, models: PdfImportModels) -> list[tuple[dict, list[float]]]:
    rows = await repo.eligible_references(REFERENCE_LIMIT)
    by_id = {}
    for row in rows:
        root, chapter = row["root_code"], row["chapter_code"]
        if root and chapter and CHAPTER_CODE.fullmatch(root) and CHAPTER_CODE.fullmatch(chapter):
            if int(root[:2]) == int(chapter[:2]) == row["grade"]:
                previous = by_id.get(row["question_id"])
                if previous is None or (previous["root_code"] == root and previous["chapter_code"] == root):
                    by_id[row["question_id"]] = row
    if not by_id:
        return []
    options = await repo.reference_options(list(by_id))
    seen = set()
    records = {}
    for question_id, row in by_id.items():
        if any("media:" in content for content in options[question_id]):
            continue
        text = embedding_text(row["content"], options[question_id])
        if text and text not in seen:
            records[question_id] = (text, hashlib.sha256(text.encode()).hexdigest())
            seen.add(text)
    if not records:
        return []
    model = models.settings.pdf_import_embedding_model
    cached = await repo.reference_vectors(model, list(records))
    vectors = {}
    missing = []
    for question_id, (text, fingerprint) in records.items():
        row = cached.get(question_id)
        if row and row.fingerprint == fingerprint:
            vectors[question_id] = row.vector
        else:
            missing.append((question_id, text, fingerprint))
    if missing:
        calculated = await models.embed([text for _, text, _ in missing])
        new_rows = []
        for (question_id, _, fingerprint), vector in zip(missing, calculated, strict=True):
            vectors[question_id] = vector
            new_rows.append({"question_id": question_id, "model": model, "fingerprint": fingerprint, "vector": vector})
        await repo.store_reference_vectors(new_rows)
    return [(by_id[question_id], unit_vector(vector)) for question_id, vector in vectors.items()]
