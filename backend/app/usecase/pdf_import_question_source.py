import re
from collections import Counter
from io import BytesIO

from pypdf import PdfReader

from app.schemas.pdf_import import ExtractedQuestion
from app.service.pdf_import_models import order_image_options
from app.usecase.pdf_import_solutions import (
    END_HEADING, QUESTION_HEADING, RAW_QUESTION_HEADING, SECTION_HEADING,
    WORKED_HEADING, heading_text, solution_key,
)

ANSWER_HEADING = re.compile(r"(?:bảng\s+)?đáp án(?:\s+trắc nghiệm)?[:.]?", re.IGNORECASE)
PAGE_NUMBER = re.compile(r"trang\s+\d+(?:\s*/\s*\d+)?", re.IGNORECASE)
IMAGE = re.compile(r"!\[[^\]\n]*\]\(media(?:-missing)?:[^)\s]+\)")
CHOICE_LABEL = re.compile(r"(?<!\S)(?:\*\*|__)?([A-D])[.)](?:\*\*|__)?(?=\s|$)")
TRUE_FALSE_LABEL = re.compile(r"(?m)^[ \t]*(?:\*\*|__)?([a-d])[.)](?:\*\*|__)?(?=\s|$)")
VECTOR_NAME = r"[A-Z]['′]?[A-Z]['′]?"
VECTOR_MATH = re.compile(
    rf"(\$\\overrightarrow\{{)({VECTOR_NAME})(\}}\s*=\s*\\overrightarrow\{{)"
    rf"({VECTOR_NAME})(\}}\$\.?)"
)
VECTOR_TEXT = re.compile(
    rf"([A-D])[.)]\s*[-−\s]*→\s*({VECTOR_NAME})\s*=\s*[-−\s]*→\s*({VECTOR_NAME})\s*\."
)
TEXT_QUESTION = re.compile(r"(?im)^\s*câu\s*(\d+)\s*[.):]")


def question_source_blocks(pages: dict[int, str]) -> dict[tuple[str, str], list[tuple[int, str]] | None]:
    """Index uniquely numbered question blocks before the key or worked solutions."""
    page_lines = {page: markdown.strip().splitlines() for page, markdown in pages.items()}
    footer_counts = Counter(
        line for lines in page_lines.values()
        if any(PAGE_NUMBER.fullmatch(heading_text(line)) for line in lines[-5:])
        for line in {line.strip() for line in lines[-5:] if line.strip()}
    )
    blocks = {}
    section = None
    current = None
    for page, lines in sorted(page_lines.items()):
        footer = next((i for i in range(max(0, len(lines) - 5), len(lines))
                       if PAGE_NUMBER.fullmatch(heading_text(lines[i]))), None)
        if footer is not None and all(
            not line.strip() or footer_counts[line.strip()] > 1 for line in lines[footer + 1:]
        ):
            lines = lines[:footer]
            while lines and not lines[-1].strip():
                lines.pop()
            if lines and lines[-1].strip().isupper() and footer_counts[lines[-1].strip()] > 1:
                lines.pop()
        for line in lines:
            heading = heading_text(line)
            if any(pattern.fullmatch(heading) for pattern in (WORKED_HEADING, END_HEADING, ANSWER_HEADING)):
                return blocks
            if part := SECTION_HEADING.match(heading):
                section, current = part[1], None
                continue
            if question := QUESTION_HEADING.match(heading):
                current = None
                raw_heading = RAW_QUESTION_HEADING.match(line)
                if section and raw_heading:
                    key = solution_key(section, question[1])
                    if key in blocks:
                        blocks[key] = None
                    else:
                        current = blocks[key] = []
                        line = line[raw_heading.end():].lstrip()
            if current is not None:
                current.append((page, line))
    return blocks


def restore_source_question(
    question: ExtractedQuestion, source: list[tuple[int, str]] | None,
) -> ExtractedQuestion:
    if not source:
        return question
    markdown = order_image_options("\n".join(line for _, line in source).strip())
    has_image = bool(IMAGE.search(markdown))
    option_label = {
        "SINGLE_CHOICE": CHOICE_LABEL, "MULTIPLE_CHOICE": CHOICE_LABEL,
        "TRUE_FALSE": TRUE_FALSE_LABEL,
    }.get(question.type)
    if not has_image and (option_label is None or len(question.statements) == 4):
        return question
    content, statements = markdown, []
    if option_label:
        labels = list(option_label.finditer(markdown))
        # Ignore label-like text before the first A/a at the start of a line.
        first = next((i for i, match in enumerate(labels) if match[1].lower() == "a"
                      and not markdown[markdown.rfind("\n", 0, match.start()) + 1:match.start()].strip()), None)
        if first is None or "".join(match[1].lower() for match in labels[first:]) != "abcd":
            return question
        labels = labels[first:]
        content = markdown[:labels[0].start()].strip()
        ends = [match.start() for match in labels[1:]] + [len(markdown)]
        statements = [markdown[match.end():end].strip() for match, end in zip(labels, ends, strict=True)]
    if not content or any(not statement for statement in statements):
        return question
    return question.model_copy(update={
        "content": content, "statements": statements,
        "pages": sorted({page for page, line in source if line.strip()}),
    })


def reconcile_vector_choices(pdf: bytes, drafts: list[dict]) -> None:
    """Check prime marks when all four vector equalities agree with the PDF text layer."""
    candidates = []
    for draft in drafts:
        options = draft["statements"]
        if draft["type"] in {"SINGLE_CHOICE", "MULTIPLE_CHOICE"} and len(options) == 4:
            matches = [VECTOR_MATH.fullmatch(option["content"].strip()) for option in options]
            if all(matches):
                candidates.append((draft, matches))
    if not candidates:
        return

    reader = PdfReader(BytesIO(pdf))
    page_text = {page: reader.pages[page - 1].extract_text()
                 for page in {page for draft, _ in candidates for page in draft["sourcePages"]}}
    for draft, matches in candidates:
        text = "\n".join(page_text[page] for page in draft["sourcePages"])
        headings = list(TEXT_QUESTION.finditer(text))
        endings = [heading.start() for heading in headings[1:]] + [len(text)]
        possible = []
        for heading, end in zip(headings, endings, strict=False):
            if heading[1] == draft["number"]:
                options = VECTOR_TEXT.findall(text[heading.end():end])
                if "".join(label for label, _, _ in options) == "ABCD":
                    possible.append(options)
        if len(possible) != 1:
            continue
        source = possible[0]
        if any(
            re.sub("['′]", "", left + right) != re.sub("['′]", "", match[2] + match[4])
            for (_, left, right), match in zip(source, matches, strict=True)
        ):
            continue
        for option, (_, left, right), match in zip(draft["statements"], source, matches, strict=True):
            option["content"] = match[1] + left.replace("′", "'") + match[3] + right.replace("′", "'") + match[5]
