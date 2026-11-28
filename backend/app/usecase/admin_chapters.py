"""Admin quản lý danh mục chương Toán THPT (#11). Không biết HTTP.

Luật:
- Mã chương dạng `<khối>C<...>` (vd `12C11`), khối 10–12, cùng khối với chương cha. Mã và slug không trùng.
- Không cho chương làm cha của chính nó hay của tổ tiên nó (kiểm bằng WITH RECURSIVE).
- Xoá chỉ khi không còn chương con và không còn câu nào gắn vào. Đổi khối của nhánh đang có câu bị chặn.
- level = level cha + 1 (gốc là 0); đổi cha thì cả nhánh dịch level theo.
"""
import re
import unicodedata

from sqlalchemy.exc import IntegrityError

from app.repositories.admin_chapter_repository import AdminChapterRepository
from app.repositories.question_bank_repository import grade_of
from app.schemas.admin_bank import ChapterIn
from app.usecase.auth import AuthError

CODE_RE = re.compile(r"^(10|11|12)C[0-9A-Za-z._-]+$")


class ChapterNotFound(AuthError):
    code = "CHAPTER_NOT_FOUND"
    message = "Không có chương này"


class ChapterCodeTaken(AuthError):
    code = "CHAPTER_CODE_TAKEN"
    message = "Mã chương hoặc slug đã được dùng"


class ChapterCycle(AuthError):
    code = "CHAPTER_CYCLE"
    message = "Không thể đặt chương làm con của chính nó hoặc của chương con cháu của nó"


class ChapterInUse(AuthError):
    code = "CHAPTER_IN_USE"
    message = "Chương đang được dùng"


class InvalidChapter(AuthError):
    code = "INVALID_CHAPTER"
    message = "Chương chưa hợp lệ"


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFD", value.replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:191] or "chuong"


def _root_grade(chapter_id: int | None, by_id: dict[int, dict]) -> int | None:
    seen = set()
    while chapter_id is not None and chapter_id in by_id and chapter_id not in seen:
        seen.add(chapter_id)
        row = by_id[chapter_id]
        if row["parent_chapter_id"] is None:
            return grade_of(row["code"] or "")
        chapter_id = row["parent_chapter_id"]
    return None


class AdminChapterUseCase:
    def __init__(self, repo: AdminChapterRepository) -> None:
        self._repo = repo

    async def tree(self, grade: int | None) -> list[dict]:
        rows = await self._repo.all_chapters()
        by_id = {r["chapter_id"]: {**r, "children": [], "question_count": 0} for r in rows}
        direct: dict[int, set[int]] = {}
        for chapter_id, question_id in await self._repo.links():
            direct.setdefault(chapter_id, set()).add(question_id)
        roots = []
        for row in by_id.values():  # rows đã sắp theo order_in_parent, chapter_id
            parent = by_id.get(row["parent_chapter_id"]) if row["parent_chapter_id"] is not None else None
            (parent["children"] if parent else roots).append(row)

        def finish(node: dict, node_grade: int | None) -> set[int]:
            node["grade"] = node_grade
            node["question_count"] = len(direct.get(node["chapter_id"], ()))
            ids = set(direct.get(node["chapter_id"], ()))
            for child in node["children"]:
                ids |= finish(child, node_grade)
            node["subtree_question_count"] = len(ids)
            return ids

        result = []
        for root in roots:
            root_grade = grade_of(root["code"] or "")
            finish(root, root_grade)
            if grade is None or root_grade == grade:
                result.append(root)
        return result

    async def _check(self, body: ChapterIn, chapter_id: int | None) -> tuple[dict | None, str, dict[int, dict]]:
        if not CODE_RE.match(body.code):
            raise InvalidChapter("Mã chương phải có dạng <khối>C<số>, vd 12C11 (khối 10–12)")
        by_id = {r["chapter_id"]: r for r in await self._repo.all_chapters()}
        parent = None
        if body.parent_chapter_id is not None:
            if chapter_id is not None and body.parent_chapter_id == chapter_id:
                raise ChapterCycle()
            parent = by_id.get(body.parent_chapter_id)
            if parent is None:
                raise ChapterNotFound("Không có chương cha này")
            if chapter_id is not None and body.parent_chapter_id in await self._repo.subtree_ids(chapter_id):
                raise ChapterCycle()
            if _root_grade(parent["chapter_id"], by_id) != grade_of(body.code):
                raise InvalidChapter("Mã chương phải cùng khối với chương cha")
        slug = body.slug or slugify(f"{body.code}-{body.name}")
        taken = await self._repo.taken(body.code, slug, chapter_id)
        if taken["code"]:
            raise ChapterCodeTaken(f"Mã chương {body.code} đã được dùng")
        if taken["slug"]:
            raise ChapterCodeTaken(f"Slug {slug} đã được dùng")
        return parent, slug, by_id

    async def _get(self, chapter_id: int) -> dict:
        for node in await self.tree(None):
            found = _find(node, chapter_id)
            if found:
                return found
        raise ChapterNotFound()

    async def create(self, body: ChapterIn) -> dict:
        parent, slug, _ = await self._check(body, None)
        subject = parent["subject_id"] if parent else await self._repo.default_subject(body.code[:3])
        if subject is None:
            raise InvalidChapter("Chưa có môn học nào để gắn chương")
        order = body.order_in_parent if body.order_in_parent is not None else await self._repo.next_order(
            body.parent_chapter_id)
        try:
            chapter_id = await self._repo.insert({
                "code": body.code, "name": body.name, "slug": slug, "parent_chapter_id": body.parent_chapter_id,
                "order_in_parent": order, "level": parent["level"] + 1 if parent else 0, "subject_id": subject,
            })
            await self._repo.commit()
        except IntegrityError:
            await self._repo.rollback()
            raise ChapterCodeTaken() from None
        return await self._get(chapter_id)

    async def update(self, chapter_id: int, body: ChapterIn) -> dict:
        current = await self._repo.get(chapter_id)
        if current is None:
            raise ChapterNotFound()
        parent, slug, by_id = await self._check(body, chapter_id)
        subtree = await self._repo.subtree_ids(chapter_id)
        old_grade = _root_grade(chapter_id, by_id)
        if old_grade != grade_of(body.code):
            children, questions = await self._repo.usage(subtree)
            if questions:
                raise ChapterInUse(f"Không thể đổi khối: nhánh chương còn {questions} câu hỏi gắn vào")
            if children and parent is None:
                raise ChapterInUse(f"Không thể đổi khối: chương còn {children} chương con")
        level = parent["level"] + 1 if parent else 0
        values = {"code": body.code, "name": body.name, "slug": slug, "parent_chapter_id": body.parent_chapter_id}
        if body.order_in_parent is not None:
            values["order_in_parent"] = body.order_in_parent
        elif body.parent_chapter_id != current["parent_chapter_id"]:
            values["order_in_parent"] = await self._repo.next_order(body.parent_chapter_id)
        if parent:
            values["subject_id"] = parent["subject_id"]
        try:
            await self._repo.update(chapter_id, values)
            await self._repo.shift_levels(subtree, level - (current["level"] or 0))
            await self._repo.commit()
        except IntegrityError:
            await self._repo.rollback()
            raise ChapterCodeTaken() from None
        return await self._get(chapter_id)

    async def delete(self, chapter_id: int) -> None:
        if await self._repo.get(chapter_id) is None:
            raise ChapterNotFound()
        children, questions = await self._repo.usage([chapter_id])
        if children or questions:
            raise ChapterInUse(f"Chương còn {children} chương con và {questions} câu hỏi gắn vào, chưa xoá được")
        await self._repo.delete(chapter_id)
        await self._repo.commit()


def _find(node: dict, chapter_id: int) -> dict | None:
    if node["chapter_id"] == chapter_id:
        return node
    for child in node["children"]:
        found = _find(child, chapter_id)
        if found:
            return found
    return None
