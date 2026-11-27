import re
import unicodedata
from dataclasses import dataclass
from itertools import groupby

WORKED_HEADING = re.compile(
    r"(?:đáp án và )?lời giải(?: chi tiết)?(?: tham khảo)?[:.]?", re.IGNORECASE
)
SECTION_HEADING = re.compile(r"phần\s+([IVXLCDM]+|\d+)(?=$|[.\s:\-–])", re.IGNORECASE)
QUESTION_HEADING = re.compile(r"câu\s+(\d+)[.):](?:\s|$)", re.IGNORECASE)
END_HEADING = re.compile(r"[-–—\s]*hết[-–—.\s]*", re.IGNORECASE)


@dataclass(frozen=True)
class WorkedSolution:
    heading: str
    chunks: tuple[tuple[int, str], ...]

    @property
    def pages(self) -> list[int]:
        return [page for page, _ in self.chunks]

    @property
    def markdown(self) -> str:
        return "\n\n".join(markdown for _, markdown in self.chunks)


def solution_key(section: str, number: str) -> tuple[str, str]:
    return section.strip().upper().removeprefix("PHẦN "), number.strip().lstrip("0") or "0"


def heading_text(line: str) -> str:
    """Ignore Markdown heading and emphasis styles while finding source boundaries."""
    return unicodedata.normalize("NFC", line).strip().lstrip("#").strip().replace("**", "").replace("__", "")


def worked_solutions(pages: dict[int, str]) -> tuple[bool, dict[tuple[str, str], WorkedSolution | None]]:
    """Copy explicitly sectioned work from the OCR. A duplicate key has no safe source."""
    found_heading = active = False
    section = None
    key = None
    blocks: dict[tuple[str, str], list[list[tuple[int, str]]]] = {}
    for page, markdown in sorted(pages.items()):
        for line in markdown.splitlines():
            heading = heading_text(line)
            if WORKED_HEADING.fullmatch(heading):
                found_heading = active = True
                section = key = None
                continue
            if not active:
                continue
            if END_HEADING.fullmatch(heading):
                active = False
                section = key = None
                continue
            if part := SECTION_HEADING.match(heading):
                section = part[1]
                key = None
                continue
            if question := QUESTION_HEADING.match(heading):
                key = solution_key(section, question[1]) if section else None
                if key is not None:
                    blocks.setdefault(key, []).append([])
            if key is not None:
                blocks[key][-1].append((page, line))

    solutions = {}
    for key, candidates in blocks.items():
        solutions[key] = None
        if len(candidates) != 1:
            continue
        lines = candidates[0]
        if not any(line.strip() for _, line in lines[1:]):
            continue
        chunks = tuple(
            (page, chunk)
            for page, group in groupby(lines, key=lambda entry: entry[0])
            if (chunk := "\n".join(line for _, line in group).strip())
        )
        solutions[key] = WorkedSolution(lines[0][1], chunks)
    return found_heading, solutions


def solution_excerpt_page(source: WorkedSolution, excerpt: str) -> int | None:
    """Allow Markdown emphasis and whitespace differences inside the matched block."""
    def compact(markdown: str) -> str:
        return "".join(" ".join(heading_text(line) for line in markdown.splitlines()).split())

    needle = compact(excerpt)
    hits = [page for page, markdown in source.chunks if needle and needle in compact(markdown)]
    return hits[0] if len(hits) == 1 else None
