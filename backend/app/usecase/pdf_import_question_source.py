import re
from collections import Counter

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
