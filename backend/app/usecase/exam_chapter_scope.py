"""Expand parent chapter allocations into leaf chapters."""
from app.usecase.exam_preview_rules import MatrixCell, PreviewEdit, PreviewStructure, allocate, apply_edit


def leaf_codes(code: str, parents: dict[str, str | None]) -> list[str]:
    pending = [code]
    seen = set()
    leaves = []
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        children = [child for child, parent in parents.items() if parent == current]
        if children:
            pending.extend(children)
        else:
            leaves.append(current)
    return leaves or [code]


def expand_chapters(structure: PreviewStructure, parents: dict[str, str | None]) -> PreviewStructure:
    if structure.rows:
        original = {(row.chapter, row.difficulty, row.type): row.count for row in structure.rows}
        expanded = {}
        for (code, difficulty, kind), count in original.items():
            for leaf, amount in allocate(count, dict.fromkeys(leaf_codes(code, parents), 1)).items():
                key = (leaf, difficulty, kind)
                expanded[key] = expanded.get(key, 0) + amount
        if original == expanded:
            return structure
        rows = [MatrixCell(chapter=key[0], difficulty=key[1], type=key[2], count=count)
                for key, count in expanded.items()]
        return apply_edit(structure, PreviewEdit(rows=rows))

    counts: dict[str, int] = {}
    for chapter in structure.chapters:
        leaves = leaf_codes(chapter.code, parents)
        for leaf, amount in allocate(chapter.count, dict.fromkeys(leaves, 1)).items():
            counts[leaf] = counts.get(leaf, 0) + amount
    if counts == {chapter.code: chapter.count for chapter in structure.chapters}:
        return structure
    return apply_edit(structure, PreviewEdit(chapter_counts=counts))
