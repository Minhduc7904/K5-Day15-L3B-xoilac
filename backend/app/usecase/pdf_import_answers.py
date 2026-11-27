import re

from app.schemas.pdf_import import AnswerEvidence, ExtractedQuestion, Extraction

CHOICE_TYPES = {"SINGLE_CHOICE", "MULTIPLE_CHOICE"}
STATEMENT_TYPES = CHOICE_TYPES | {"TRUE_FALSE"}
MEDIA_ID = re.compile(r"media:(\d+)")
MISSING_MEDIA = re.compile(r"media-missing:p\d+-\d+")
LETTERED_OPTION = re.compile(r"^\s*(?:\*\*)?([A-D])[.)](?:\*\*)?\s+(.+)$", re.DOTALL)


def media_ids(*values: str | None) -> set[int]:
    return {int(item) for value in values if value for item in MEDIA_ID.findall(value)}


def answer_value(question: ExtractedQuestion, evidence: AnswerEvidence):
    count = len(question.statements)
    if question.type in CHOICE_TYPES:
        indexes = evidence.choices or []
        if not indexes or len(set(indexes)) != len(indexes) or any(i < 1 or i > count for i in indexes):
            return None
        if question.type == "SINGLE_CHOICE" and len(indexes) != 1:
            return None
        return tuple(sorted(indexes))
    if question.type == "TRUE_FALSE":
        values = evidence.truth_values
        if values and len(values) == count:
            return tuple(values)
        return None
    return evidence.answer.strip() if evidence.answer and evidence.answer.strip() else None


def comparable_answer(value: str) -> str:
    stripped = value.strip().removeprefix("$").removesuffix("$").strip()
    if re.fullmatch(r"-?\d+(?:[.,]\d+)?", stripped):
        return stripped.replace(",", ".")
    return value


def normalize_extracted_question(question: ExtractedQuestion, source: str) -> ExtractedQuestion:
    """Recover stem fragments when the source has explicit, ordered option labels."""
    statements = question.statements
    if question.type not in STATEMENT_TYPES:
        if statements:
            stem = "\n\n".join([question.content, *statements])
            return question.model_copy(update={"content": stem, "statements": []})
        return question
    if question.type not in CHOICE_TYPES or len(statements) < 4:
        return question
    prefix = statements[:-4]
    if any(LETTERED_OPTION.match(value) for value in prefix):
        return question
    options = statements[-4:]
    labeled = [LETTERED_OPTION.fullmatch(value) for value in options]
    if all(labeled) and [match[1] for match in labeled] == list("ABCD"):
        options = [match[2] for match in labeled]
    elif not prefix or any(labeled):
        return question
    else:
        # A model may already have removed the option labels. Require the same
        # four options with ordered labels together on a source page.
        block = "".join(
            rf"(?:\*\*)?{label}[.)](?:\*\*)?{re.escape(''.join(value.split()))}"
            for label, value in zip("ABCD", options)
        )
        if not re.search(block, "".join(source.split())):
            return question
    return question.model_copy(update={
        "content": "\n\n".join([question.content, *prefix]),
        "statements": options,
    })


def table_cells(line: str) -> tuple[str, ...]:
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return ()
    return tuple(" ".join(cell.split()) for cell in line[1:-1].split("|"))


def anchor_evidence(
    item: AnswerEvidence, normalized_pages: dict[int, str], table_pages: dict[tuple[str, ...], set[int]]
) -> AnswerEvidence | None:
    excerpt = " ".join(item.excerpt.split())
    if excerpt and excerpt in normalized_pages.get(item.page, ""):
        return item
    cells = table_cells(item.excerpt)
    if item.source == "key" and cells and cells[0] == item.number:
        hits = table_pages.get(cells, set())
        if len(hits) == 1:
            return item.model_copy(update={"page": next(iter(hits))})
    return None


def build_drafts(extraction: Extraction, pages: list[dict]) -> list[dict]:
    page_map = {page["page"]: page["normalized"] for page in pages}
    normalized_pages = {number: " ".join(markdown.split()) for number, markdown in page_map.items()}
    table_pages: dict[tuple[str, ...], set[int]] = {}
    for number, markdown in page_map.items():
        for line in markdown.splitlines():
            cells = table_cells(line)
            if cells and cells[0].isdigit():
                table_pages.setdefault(cells, set()).add(number)
    answers = [
        anchored for item in extraction.answers
        if (anchored := anchor_evidence(item, normalized_pages, table_pages)) is not None
    ]
    source_media = {number: media_ids(value) for number, value in page_map.items()}
    keys = [(q.section, q.number) for q in extraction.questions]
    if len(set(keys)) != len(keys):
        raise ValueError("Trùng số câu trong cùng một phần.")
    drafts = []
    for extracted in extraction.questions:
        if not extracted.pages or not set(extracted.pages) <= page_map.keys():
            raise ValueError("Câu hỏi thiếu trang nguồn hợp lệ.")
        source = "\n".join(page_map[page] for page in sorted(set(extracted.pages)))
        question = normalize_extracted_question(extracted, source)
        matching = []
        source_excerpts = []
        ambiguous = False
        for item in answers:
            if item.number != question.number or item.section not in (None, question.section):
                continue
            source_excerpts.append(item)
            if item.section is None and sum(number == item.number for _, number in keys) != 1:
                ambiguous = True
                continue
            matching.append(item)
        values = [answer_value(question, item) for item in matching]
        known = [value for value in values if value is not None]
        solutions = [item.solution for item in matching if item.source == "solution" and item.solution]
        solution = "\n\n".join(dict.fromkeys(solutions)) or None
        value = known[0] if known else None
        if question.type == "TRUE_FALSE" and known:
            candidates = [{value for value in column if value is not None} for column in zip(*known)]
            conflict = any(len(column) > 1 for column in candidates)
            value = tuple(next(iter(column)) if len(column) == 1 else None for column in candidates)
        else:
            values_to_compare = [comparable_answer(item) if isinstance(item, str) else item for item in known]
            conflict = len(set(values_to_compare)) > 1
        state = "resolved"
        if conflict:
            state, value = "conflict", None
        elif ambiguous and value is None:
            state, value = "ambiguous", None
        elif value is None or (question.type == "TRUE_FALSE" and None in value):
            state = "missing"
        flags = [] if state == "resolved" else [f"answer_{state}"]
        if question.image_dependent:
            flags.append("image_review")
        source_pages = set(question.pages) | {item.page for item in matching if item.source == "solution"}
        content_fields = [question.content, *question.statements, solution or ""]
        source_ids = set().union(*(source_media[number] for number in source_pages))
        if media_ids(*content_fields) - source_ids:
            flags.append("image_source_mismatch")
        if any(MISSING_MEDIA.search(field) for field in content_fields):
            flags.append("image_missing")
        options = []
        for i, content in enumerate(question.statements):
            correct = None
            if value is not None and question.type in CHOICE_TYPES:
                correct = i + 1 in value
            elif value is not None and question.type == "TRUE_FALSE":
                correct = value[i]
            options.append({"content": content, "isCorrect": correct})
        drafts.append({
            "section": question.section, "number": question.number, "sourcePages": sorted(set(question.pages)),
            "type": question.type, "content": question.content, "statements": options,
            "correctAnswer": value if isinstance(value, str) else None, "solution": solution,
            "answerState": state, "evidence": [item.model_dump() for item in source_excerpts],
            "flags": flags, "imageDependent": question.image_dependent, "imageReviewed": False,
            "chapterCodes": [], "difficulty": None, "suggestions": None,
        })
    placed = set().union(*(media_ids(
        draft["content"], draft["solution"], *(item["content"] for item in draft["statements"])
    ) for draft in drafts))
    for draft in drafts:
        pages_with_questions = draft["sourcePages"]
        fields = [draft["content"], draft["solution"] or "", *(item["content"] for item in draft["statements"])]
        visible_missing = set(MISSING_MEDIA.findall("\n".join(fields)))
        if any(source_media[page] - placed or set(MISSING_MEDIA.findall(page_map[page])) - visible_missing
               for page in pages_with_questions):
            draft["flags"].append("image_unplaced")
    return drafts
