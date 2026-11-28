"""Luồng nghiệp vụ pipeline học sinh tạo đề ôn (issue #4).

Một phiên có tin nhắn và đúng một bản xem trước hiện tại, ở một trong hai chế độ:
- CHAPTER: ôn theo chương (chương yếu từ lịch sử làm bài, hoặc chương học sinh chọn); học sinh chỉnh tự do.
- EXAM_TEMPLATE: ôn theo một mẫu kỳ thi đã duyệt (#5); mẫu cố định phần, loại câu, số câu, độ khó, học sinh chỉ
  thu hẹp được chương. Chỉnh sửa vi phạm ràng buộc của mẫu bị từ chối kèm lý do.

Học sinh chỉnh bằng chat (respond) hoặc qua API (update_preview); cả hai cùng dùng một bộ luật và cùng kiểm version
để không ghi đè nhau. Chỉ sau khi xác nhận mới chọn câu từ ngân hàng đã duyệt để dựng đề nháp; đề nháp không có
đáp án, cờ đúng/sai hay lời giải.

Chủ sở hữu: khi có người gọi (Requester, lấy từ đăng nhập), học sinh chỉ thấy phiên của chính mình; phiên của người
khác được coi như không tồn tại (SessionNotFound → 404), để không lộ phiên đó có thật.

Hành vi bám codebase/agent.py (lát cắt đã đo): chặn trước, hỏi lại khi thiếu hoặc mâu thuẫn, không bịa câu.
Test đối chiếu: tests/test_agent_parity.py.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.models.exam_chat import ExamChatSession, ExamDraft, ExamPreview
from app.repositories.exam_chat_repository import ExamChatRepository
from app.repositories.question_bank_repository import QuestionBankRepository, grade_of
from app.service.exam_chat_sources import MIN_ANSWERED, ExamTemplateSource, StudentHistorySource
from app.service.media_image import load_media_image
from app.usecase import exam_chat_intent as chat_intent
from app.usecase.exam_preview_rules import (
    DEFAULT_TOTAL,
    DIFF_NAME,
    MAX_TOTAL,
    PreviewEdit,
    PreviewRuleError,
    PreviewStructure,
    apply_edit,
    can_confirm,
    check_structure,
    describe,
    difficulty_plan,
    matrix_plan,
    new_structure,
)
from app.usecase.exam_scoring import allocate_points
from app.usecase.exam_template_plan import (
    EXAM_NAME,
    TYPE_NAME,
    TemplateConflict,
    TemplatePreviewStructure,
    apply_template_edit,
    describe_template,
    from_template,
)

CLOSE_GAP = 0.10     # hai chương yếu nhất cách nhau ≤ 10 điểm % → chia câu cho cả hai
VN_TZ = timezone(timedelta(hours=7))
CHAPTER_PHRASE = re.compile(r"chuong\s+([a-z0-9 ]+?)(?:\s+cho\b|\s+\d|[,.;:!?(]|$)")
SWITCH_TO_CHAPTER = re.compile(r"(theo chuong|chuyen sang on chuong|bo mau|khong theo mau)")

Structure = PreviewStructure | TemplatePreviewStructure


DIFFICULTY_ORDER = ("NB", "TH", "VD", "VDC")


@dataclass
class _Slot:
    """Một ô của ma trận: câu khớp chính xác, số câu cần, nhãn gắn vào câu và điều kiện để bù khi thiếu."""
    ids: list[int]
    wanted: int
    meta: dict
    fill: dict
    shortage: dict
    outside: set[int] = field(default_factory=set)


class SessionNotFound(Exception):
    pass


class PreviewNotFound(Exception):
    pass


class VersionConflict(Exception):
    def __init__(self, current: int) -> None:
        super().__init__(f"Bản xem trước đã đổi (version hiện tại {current})")
        self.current = current


class InvalidState(Exception):
    pass


class MissingStudent(Exception):
    """Tạo phiên mà không có người đăng nhập lẫn mã học sinh."""


@dataclass(frozen=True)
class Requester:
    """Người gọi API, lấy từ phiên đăng nhập (Auth #8). student_ref là mã dùng để tra lịch sử làm bài."""

    user_id: int
    student_ref: str


@dataclass
class ChatTurn:
    """Kết quả một lượt chat để tầng API phát thành sự kiện SSE."""

    reply: str
    preview: ExamPreview | None = None
    preview_changed: bool = False
    draft: ExamDraft | None = None
    notes: list[str] = field(default_factory=list)


def draft_title(now: datetime | None = None) -> str:
    day = (now or datetime.now(VN_TZ)).astimezone(VN_TZ)
    return f"Đề ôn luyện ngày {day:%d/%m/%Y}"


def load_structure(preview: ExamPreview) -> Structure:
    if preview.mode == "EXAM_TEMPLATE":
        return TemplatePreviewStructure.model_validate(preview.structure)
    return PreviewStructure.model_validate(preview.structure)


class ExamChatUseCase:
    def __init__(
        self,
        repo: ExamChatRepository,
        bank: QuestionBankRepository,
        history: StudentHistorySource,
        templates: ExamTemplateSource,
    ) -> None:
        self._repo = repo
        self._bank = bank
        self._history = history
        self._templates = templates

    # ---------- phiên và quyền sở hữu ----------

    async def create_session(self, student_ref: str | None, requester: Requester | None = None) -> ExamChatSession:
        if requester is not None:
            return await self._repo.create_session(requester.student_ref, user_id=requester.user_id)
        if not student_ref or not student_ref.strip():
            raise MissingStudent()
        return await self._repo.create_session(student_ref.strip())

    async def _session(self, session_id: int, requester: Requester | None) -> ExamChatSession:
        item = await self._repo.get_session(session_id)
        if item is None or item.deleted_at is not None or (requester is not None and item.user_id != requester.user_id):
            raise SessionNotFound()
        return item

    async def list_sessions(self, requester: Requester):
        return await self._repo.list_sessions(requester.user_id)

    async def rename_session(self, session_id: int, requester: Requester, title: str) -> ExamChatSession:
        item = await self._session(session_id, requester)
        await self._repo.rename_session(item, title.strip())
        return item

    async def delete_session(self, session_id: int, requester: Requester) -> None:
        await self._repo.hide_session(await self._session(session_id, requester))

    async def check_owner(self, session_id: int, requester: Requester) -> None:
        await self._session(session_id, requester)

    async def message_page(self, session_id: int, requester: Requester, before: int | None, limit: int):
        await self._session(session_id, requester)
        return await self._repo.message_page(session_id, before, limit)

    async def list_drafts(self, requester: Requester):
        return await self._repo.list_drafts(requester.user_id)

    async def draft_by_id(self, requester: Requester, draft_id: int) -> ExamDraft:
        draft = await self._repo.draft_by_id(requester.user_id, draft_id)
        if draft is None:
            raise SessionNotFound()
        return draft

    async def draft_media(self, requester: Requester, draft_id: int, media_id: int, storage):
        draft = await self.draft_by_id(requester, draft_id)
        marker = f"](media:{media_id})"
        if not any(marker in item["content"] or any(marker in row["content"] for row in item["statements"])
                   for item in draft.items):
            raise SessionNotFound()
        result = await load_media_image(storage, await self._repo.media_object(media_id))
        if not result:
            raise SessionNotFound()
        return result

    async def chat_attachment(self, session_id: int, requester: Requester, attachment_id: int, storage):
        await self._session(session_id, requester)
        image = await self._repo.chat_attachment(session_id, attachment_id)
        if image is None:
            raise SessionNotFound()
        key, mime = image
        stored = await storage.get(key)
        if stored is None:
            raise SessionNotFound()
        return stored[0], mime

    async def chapter_catalog(self):
        return await self._bank.chapter_catalog()

    async def get_state(self, session_id: int, requester: Requester | None = None):
        session = await self._session(session_id, requester)
        messages = await self._repo.list_messages(session_id)
        preview = await self._repo.get_preview(session_id)
        draft = await self._repo.latest_draft(session_id)
        return session, messages, preview, draft

    async def get_preview(self, session_id: int, requester: Requester | None = None) -> ExamPreview:
        await self._session(session_id, requester)
        preview = await self._repo.get_preview(session_id)
        if preview is None:
            raise PreviewNotFound()
        return preview

    async def latest_draft(self, session_id: int, requester: Requester | None = None) -> ExamDraft | None:
        await self._session(session_id, requester)
        return await self._repo.latest_draft(session_id)

    # ---------- đường chỉnh qua API ----------

    async def update_preview(
        self, session_id: int, edit: PreviewEdit, expected_version: int, requester: Requester | None = None
    ) -> ExamPreview:
        preview = await self.get_preview(session_id, requester)
        if preview.version != expected_version:
            raise VersionConflict(preview.version)
        structure = await self._edited(load_structure(preview), edit)   # TemplateConflict / PreviewRuleError
        return await self._repo.save_preview(
            session_id, {"structure": structure.model_dump(mode="json"), "status": "EDITED"}
        )

    async def confirm(
        self, session_id: int, expected_version: int, requester: Requester | None = None
    ) -> tuple[ExamPreview, ExamDraft | None, str]:
        preview = await self.get_preview(session_id, requester)
        if preview.version != expected_version:
            raise VersionConflict(preview.version)
        if not can_confirm(preview.status):
            raise InvalidState(f"Bản xem trước đang ở trạng thái {preview.status}, chỉnh lại trước khi xác nhận.")
        return await self._confirm_and_build(session_id, preview)

    # ---------- đường chỉnh qua chat ----------

    async def respond(self, session_id: int, text: str, requester: Requester | None = None) -> ChatTurn:
        session = await self._session(session_id, requester)
        await self._repo.add_message(session_id, "student", text)
        turn = await self._decide(session, text)
        version = turn.preview.version if turn.preview is not None else None
        await self._repo.add_message(session_id, "assistant", turn.reply, version)
        return turn

    async def _decide(self, session: ExamChatSession, text: str) -> ChatTurn:
        intent = chat_intent.read(text)
        sid = session.session_id
        current = await self._repo.get_preview(sid)
        on_template = current is not None and current.mode == "EXAM_TEMPLATE" \
            and not SWITCH_TO_CHAPTER.search(chat_intent.norm(text))

        if intent.kind == "refuse":
            return ChatTurn(intent.text, notes=["chặn trước AI"])
        if intent.kind == "exam":
            return await self._exam_branch(sid, intent.exam or {})
        if on_template and intent.kind in ("confirm", "edit"):
            return await self._template_turn(sid, current, intent)
        if intent.asked_total is not None and intent.asked_total > MAX_TOTAL and intent.kind != "confirm":
            return ChatTurn(f"Một đề ôn tối đa {MAX_TOTAL} câu. Em chọn số câu nhỏ hơn nhé.")

        chapter_current = None if current is None or current.mode == "EXAM_TEMPLATE" else current
        if intent.kind == "confirm":
            return await self._chat_confirm(sid, chapter_current, intent)
        if intent.kind == "edit":
            return await self._chat_edit(sid, chapter_current, intent.edit)

        unknown = await self._unknown_chapter(text, intent)
        if unknown:
            return ChatTurn(unknown, notes=["thu hẹp: chương không có trong ngân hàng"])
        if intent.kind == "weak":
            return await self._weak_branch(session, intent.edit)
        return ChatTurn("Em muốn ôn chương nào, hay để mình chọn theo chương em hay sai? " + chat_intent.OFFER)

    # ---------- nhánh ôn theo mẫu kỳ thi ----------

    async def _exam_branch(self, sid: int, exam: dict) -> ChatTurn:
        if not exam.get("exam_type"):
            return ChatTurn("Em muốn ôn theo kỳ thi nào: giữa kỳ hay cuối kỳ, học kỳ 1 hay 2, lớp mấy? "
                            "Hoặc thi tốt nghiệp THPT, HSA, TSA?", notes=["hỏi lại: thiếu loại kỳ thi"])
        found = await self._templates.find(exam["exam_type"], exam.get("grade"), exam.get("version_label"))
        if not found:
            return ChatTurn("Mình chưa có cấu trúc đã xác thực nguồn cho kỳ thi này nên không nêu số câu hay phân bố "
                            "chương, để khỏi nói sai. " + chat_intent.OFFER, notes=["thu hẹp: chưa có mẫu đã duyệt"])
        if len(found) > 1:
            options = "\n".join("- " + self._template_label(t) for t in found)
            return ChatTurn(f"Có {len(found)} mẫu đã duyệt cho kỳ thi {EXAM_NAME.get(exam['exam_type'], '')}:\n{options}\n"
                            "Em nhắn lại kèm khối hoặc năm (ví dụ \"lớp 11\", \"2025\") để mình chọn đúng một mẫu nhé.",
                            notes=["hỏi lại: nhiều mẫu phù hợp"])
        structure = from_template(found[0])
        reason = f"Theo mẫu đã duyệt \"{structure.template_name}\"."
        preview = await self._repo.save_preview(sid, {
            "structure": structure.model_dump(mode="json"), "status": "PROPOSED", "mode": "EXAM_TEMPLATE",
            "reason": reason,
        })
        names = await self._bank.chapter_names()
        reply = ("Đề xuất đề ôn theo mẫu kỳ thi (chưa tạo đề):\n" + describe_template(structure, names) + "\n"
                 "Mẫu cố định số câu và độ khó; em có thể thu hẹp chương trong phạm vi mẫu, rồi xác nhận để mình tạo đề.")
        return ChatTurn(reply, preview=preview, preview_changed=True, notes=["preview theo mẫu kỳ thi"])

    @staticmethod
    def _template_label(t: dict) -> str:
        parts = [t.get("name", "")]
        if t.get("grade"):
            parts.append(f"lớp {t['grade']}")
        if t.get("version_label"):
            parts.append(str(t["version_label"]))
        parts.append(f"{t.get('total_questions', '?')} câu")
        return " · ".join(parts)

    async def _template_turn(self, sid: int, current: ExamPreview, intent) -> ChatTurn:
        structure = load_structure(current)
        try:
            structure = apply_template_edit(structure, intent.edit)
        except TemplateConflict as e:
            return ChatTurn("Chỉnh này xung đột với mẫu kỳ thi: " + " ".join(e.errors) + " Nếu muốn tự chọn số câu "
                            "và độ khó, em nhắn \"ôn theo chương ...\" để chuyển sang ôn theo chương.",
                            notes=["từ chối: xung đột ràng buộc mẫu"])
        changed = structure.model_dump() != load_structure(current).model_dump()
        if changed or current.status not in ("PROPOSED", "EDITED"):
            current = await self._repo.save_preview(sid, {"structure": structure.model_dump(mode="json"),
                                                          "status": "EDITED"})
        if intent.kind == "confirm":
            preview, draft, reply = await self._confirm_and_build(sid, current)
            return ChatTurn(reply, preview=preview, preview_changed=True, draft=draft)
        names = await self._bank.chapter_names()
        reply = "Đã cập nhật đề theo mẫu (chưa tạo đề):\n" + describe_template(structure, names) + "\n" + self._ask_confirm()
        return ChatTurn(reply, preview=current, preview_changed=True)

    # ---------- nhánh ôn theo chương ----------

    async def _chat_confirm(self, sid: int, current: ExamPreview | None, intent) -> ChatTurn:
        edit: PreviewEdit = intent.edit
        if intent.asked_total is not None and intent.asked_total > MAX_TOTAL:
            # Học sinh xác nhận một số câu vượt giới hạn: vẫn dựng tối đa trong ngân hàng, báo rõ.
            edit = edit.model_copy(update={"total": None})
        if edit.chapter_codes or edit.chapter_counts:
            structure = new_structure({c: 1 for c in (edit.chapter_codes or edit.chapter_counts)}, edit)
            if edit.total is None and not edit.chapter_counts:
                structure = apply_edit(structure, PreviewEdit(total=self._asked(intent, current)))
        elif current is not None:
            structure = apply_edit(PreviewStructure.model_validate(current.structure), edit)
        else:
            return ChatTurn("Mình chưa có cấu trúc đề nào để xác nhận. Em muốn ôn chương nào?")
        errors = await self._errors(structure)
        if errors:
            return ChatTurn("Cấu trúc chưa hợp lệ: " + " ".join(errors))
        preview = await self._repo.save_preview(
            sid, {"structure": structure.model_dump(mode="json"), "status": "EDITED", "mode": "CHAPTER", "reason": None}
        )
        preview, draft, reply = await self._confirm_and_build(sid, preview)
        if intent.asked_total is not None and intent.asked_total > MAX_TOTAL:
            reply += f"\nLưu ý: một đề ôn tối đa {MAX_TOTAL} câu nên mình không dựng {intent.asked_total} câu."
        return ChatTurn(reply, preview=preview, preview_changed=True, draft=draft)

    def _asked(self, intent, current: ExamPreview | None) -> int:
        if intent.asked_total is not None:
            return min(intent.asked_total, MAX_TOTAL)
        if current is not None:
            return PreviewStructure.model_validate(current.structure).total
        return DEFAULT_TOTAL

    async def _chat_edit(self, sid: int, current: ExamPreview | None, edit: PreviewEdit) -> ChatTurn:
        if current is not None:
            structure = apply_edit(PreviewStructure.model_validate(current.structure), edit)
        elif edit.chapter_codes or edit.chapter_counts:
            base = edit.chapter_counts or {c: 1 for c in edit.chapter_codes or []}
            structure = new_structure(base, edit)
            if edit.total is None and not edit.chapter_counts:
                structure = apply_edit(structure, PreviewEdit(total=DEFAULT_TOTAL))
        else:
            return ChatTurn("Em muốn ôn chương nào? Ví dụ: 12C1, 12C4.")
        errors = await self._errors(structure)
        if errors:
            return ChatTurn("Mình chưa đổi được cấu trúc: " + " ".join(errors))
        status = "EDITED" if current is not None else "PROPOSED"
        preview = await self._repo.save_preview(
            sid, {"structure": structure.model_dump(mode="json"), "status": status, "mode": "CHAPTER",
                  **({} if current is not None else {"reason": None})}
        )
        names = await self._bank.chapter_names()
        reply = "Đề xuất cấu trúc đề ôn (chưa tạo đề):\n" + describe(structure, names) + "\n" + self._ask_confirm()
        return ChatTurn(reply, preview=preview, preview_changed=True)

    async def _weak_branch(self, session: ExamChatSession, edit: PreviewEdit) -> ChatTurn:
        history = await self._history.get(session.student_ref)
        if history is None or not history.chapters:
            return ChatTurn(f"Mình chưa có lịch sử làm bài của {session.student_ref} nên chưa biết chương em hay sai, "
                            "và mình không đoán. Em muốn ôn chương nào?", notes=["dừng: chưa có lịch sử"])
        ranked = sorted((c for c in history.chapters if c.total >= MIN_ANSWERED
                         and (history.latest_at is None or c.classification == "weak")), key=lambda c: (c.rate, c.code))
        if history.latest_at and not history.attempt_count:
            return ChatTurn("Em chưa có lượt đã chấm trong khoảng thời gian gần đây. Em muốn chọn chương nào để ôn?")
        if history.conflicting:
            lines = "\n".join(f"- {c.code}: đúng {c.correct}/{c.total} ({round(100 * c.rate)}%)" for c in ranked[:3])
            return ChatTurn(f"Kết quả làm bài của {session.student_ref} có chỗ mâu thuẫn (khoảng "
                            f"{round(100 * history.conflict_ratio)}% số câu vừa đúng vừa sai trong cùng một lượt), nên "
                            f"mình chưa xác định chắc chương yếu. Các chương đang thấp nhất:\n{lines}\n"
                            "Em muốn ôn chương nào trong số này, hay chương khác?", notes=["dừng: dữ liệu mâu thuẫn"])
        if not ranked:
            return ChatTurn("Chưa xác định được chương yếu từ số câu đã làm. Em muốn chọn chương nào để ôn?")
        # + 1e-9: để khoảng cách đúng 10 điểm % (vd 40% − 30%) không bị sai số dấu phẩy động loại ra.
        top = ranked[:2] if len(ranked) >= 2 and ranked[1].rate - ranked[0].rate <= CLOSE_GAP + 1e-9 else ranked[:1]
        n = edit.total or DEFAULT_TOTAL
        if len(top) == 2:
            first = round(n * 0.6)
            counts = {top[0].code: first, top[1].code: n - first}
        else:
            counts = {top[0].code: n}
        structure = new_structure({c: k for c, k in counts.items() if k > 0},
                                  edit.model_copy(update={"total": None, "chapter_codes": None, "chapter_counts": None}))
        reason = "Lý do: " + "; ".join(
            f"{c.code} đúng {c.correct}/{c.total} ({round(100 * c.rate)}%), sai {c.total - c.correct}/{c.total} câu"
            for c in top
        ) + (", hai chương yếu gần nhau nên chia câu cho cả hai." if len(top) == 2 else ".")
        if history.latest_at:
            reason = "Gợi ý theo quy tắc. " + reason
        preview = await self._repo.save_preview(
            session.session_id,
            {"structure": structure.model_dump(mode="json"), "status": "PROPOSED", "mode": "CHAPTER", "reason": reason},
        )
        names = await self._bank.chapter_names()
        reply = "Đề xuất cấu trúc đề ôn (chưa tạo đề):\n" + describe(structure, names) + f"\n{reason}\n" + self._ask_confirm()
        return ChatTurn(reply, preview=preview, preview_changed=True)

    async def _unknown_chapter(self, text: str, intent) -> str | None:
        """Học sinh gọi tên một chương mà danh mục không có (vd "Số phức"): nói rõ, không bịa câu."""
        if intent.edit.chapter_codes or intent.edit.chapter_counts:
            return None
        t = chat_intent.norm(text)
        m = CHAPTER_PHRASE.search(t)
        if not m or chat_intent.WEAK.search(m.group(1)):
            return None
        phrase = m.group(1).strip()
        names = await self._bank.chapter_names()
        if any(phrase in chat_intent.norm(name) for name in names.values()):
            return None
        shown = re.search(r"chương\s+([^\d,.;:!?(]+?)(?:\s+cho\b|\s+\d|[,.;:!?(]|$)", text, re.I)
        name = (shown.group(1) if shown else phrase).strip()
        return (f"Ngân hàng hiện chưa có câu hỏi về chương \"{name}\", nên mình không bịa câu. "
                "Em chọn chương khác nhé, ví dụ: 12C1, 12C4.")

    @staticmethod
    def _ask_confirm() -> str:
        return "Em xác nhận hoặc chỉnh bằng lời (đổi chương, số câu, độ khó) nhé."

    # ---------- kiểm tra ----------

    async def _errors(self, structure: PreviewStructure) -> list[str]:
        names = await self._bank.chapter_names()
        return check_structure(structure, set(names) if names else None)

    async def _edited(self, structure: Structure, edit: PreviewEdit) -> Structure:
        """Một luật cho cả chat và API: mẫu kỳ thi thì kiểm ràng buộc của mẫu, còn lại kiểm luật cấu trúc chương."""
        if isinstance(structure, TemplatePreviewStructure):
            return apply_template_edit(structure, edit)
        edited = apply_edit(structure, edit)
        errors = await self._errors(edited)
        if errors:
            raise PreviewRuleError(errors)
        return edited

    # ---------- dựng đề ----------

    async def _confirm_and_build(self, sid: int, preview: ExamPreview) -> tuple[ExamPreview, ExamDraft | None, str]:
        structure = load_structure(preview)
        if isinstance(structure, PreviewStructure):
            errors = await self._errors(structure)
            if errors:
                raise PreviewRuleError(errors)
        confirmed = await self._repo.save_preview(sid, {"status": "CONFIRMED"})
        if isinstance(structure, TemplatePreviewStructure):
            chosen, meta, shortages = await self._pick_template(structure)
        else:
            chosen, meta, shortages = await self._pick_chapters(structure)
        loaded = await self._bank.load_items(chosen)
        items = []
        for qid in chosen:
            if qid not in loaded:          # chặn sau: chỉ câu còn đọc được trong ngân hàng đã duyệt
                continue
            q = dict(loaded[qid])
            info = meta[qid]
            q["chapter"] = info.get("chapter") or next(iter(q.get("chapter_codes") or []), None)
            items.append({"order": len(items) + 1, **q, **{k: v for k, v in info.items() if k != "chapter"}})
        if not items:
            preview = await self._repo.save_preview(sid, {"status": "EDITED"})
            return preview, None, ("Ngân hàng chưa có câu nào phù hợp cấu trúc này, nên mình không tạo đề và không bịa "
                                   "câu. Em thử đổi chương hoặc độ khó nhé.")
        items = allocate_points(items, structure.model_dump(mode="json"))
        draft = await self._repo.add_draft({
            "session_id": sid,
            "preview_version": confirmed.version,
            "title": getattr(structure, "title", None) or draft_title(),
            "structure": structure.model_dump(mode="json"),
            "items": items,
            "shortages": shortages,
        })
        await self._repo.notify_draft_ready(sid, draft)
        preview = await self._repo.save_preview(sid, {"status": "BUILT"})
        return preview, draft, self._draft_text(draft, structure)

    async def _pick_chapters(self, structure: PreviewStructure):
        slots: list[_Slot] = []
        scope = [item.code for item in structure.chapters]
        allowed = [d for d in DIFFICULTY_ORDER if d in structure.effective_weights()] or None
        if structure.rows or structure.type_counts:
            for cell in matrix_plan(structure):
                result = await self._bank.pick_for_section(
                    question_type=cell.type, n=cell.count, chapter_codes=[cell.chapter],
                    difficulty=cell.difficulty, exclude=[i for slot in slots for i in slot.ids],
                )
                slots.append(_Slot(
                    result.question_ids, cell.count, {"chapter": cell.chapter},
                    dict(question_type=cell.type, chapters=[cell.chapter], difficulty=cell.difficulty,
                         grade=grade_of(cell.chapter), scope=scope, allowed=allowed),
                    {"chapter": cell.chapter, "difficulty": cell.difficulty, "question_type": cell.type},
                ))
            return await self._settle(slots)
        for code, mix in difficulty_plan(structure).items():
            for diff, k in mix.items():
                res = await self._bank.pick(code, diff, k, exclude=[i for slot in slots for i in slot.ids])
                slots.append(_Slot(
                    res.question_ids, k, {"chapter": code},
                    dict(question_type=None, chapters=[code], difficulty=diff, grade=grade_of(code), scope=scope,
                         allowed=allowed),
                    {"chapter": code, "difficulty": diff},
                ))
        return await self._settle(slots)

    async def _pick_template(self, structure: TemplatePreviewStructure, *, prefer_subchapters: bool = False):
        slots: list[_Slot] = []
        for sec in structure.sections:
            chapters = sec.effective_chapters()
            for diff, k in sec.difficulty_plan().items():
                res = await self._bank.pick_for_section(question_type=sec.question_type, n=k, chapter_codes=chapters,
                                                        difficulty=diff, grade=structure.grade,
                                                        exclude=[i for slot in slots for i in slot.ids],
                                                        prefer_subchapters=prefer_subchapters)
                slots.append(_Slot(
                    res.question_ids, k,
                    {"section_order": sec.order, "section_title": sec.title, "points": sec.points_per_question},
                    dict(question_type=sec.question_type, chapters=chapters, difficulty=diff, grade=structure.grade,
                         scope=sec.allowed_chapters, prefer_subchapters=prefer_subchapters),
                    {"section_order": sec.order, "section_title": sec.title, "question_type": sec.question_type,
                     "chapter": ", ".join(chapters) if chapters else None, "difficulty": diff},
                ))
        return await self._settle(slots)

    async def _settle(self, slots: list["_Slot"]):
        """Bù ô thiếu bằng câu thay thế, giữ nguyên thứ tự ô. Chỉ còn báo thiếu khi kho hết câu cùng loại."""
        for slot in slots:
            missing = slot.wanted - len(slot.ids)
            if missing > 0:
                taken = await self._fill_gap(exclude=[i for other in slots for i in other.ids], n=missing, **slot.fill)
                slot.ids += [qid for qid, _ in taken]
                slot.outside.update(qid for qid, same_chapter in taken if not same_chapter)
        chosen: list[int] = []
        meta: dict[int, dict] = {}
        shortages: list[dict] = []
        for slot in slots:
            chosen += slot.ids
            for qid in slot.ids:
                # Câu bù từ chương khác: bỏ nhãn chương của ô để đề hiện đúng chương thật của câu.
                meta[qid] = {k: v for k, v in slot.meta.items() if k != "chapter" or qid not in slot.outside}
            if len(slot.ids) < slot.wanted:
                shortages.append({**slot.shortage, "requested": slot.wanted, "available": len(slot.ids)})
        return chosen, meta, shortages

    async def _fill_gap(
        self, *, exclude: list[int], n: int, question_type: str | None, chapters: list[str] | None,
        difficulty: str | None, grade: int | None, scope: list[str] | None = None, prefer_subchapters: bool = False,
        allowed: list[str] | None = None,
    ) -> list[tuple[int, bool]]:
        """Bù n câu cho ô thiếu theo thứ tự ưu tiên, luôn giữ đúng loại câu: cùng chương (mức khó gần nhất trước),
        rồi cùng mức khó ở chương khác (chương trong phạm vi đề trước), cuối cùng bất kỳ câu cùng loại trong khối.
        `allowed` là các mức khó học sinh còn cho phép (không lấy mức đã loại). Trả về (mã câu, câu có thuộc chương của ô hay không)."""
        taken: list[tuple[int, bool]] = []

        async def take(same_chapter: bool, **where) -> None:
            need = n - len(taken)
            if need <= 0:
                return
            found = await self._bank.pick_for_section(
                question_type=question_type, n=need, exclude=[*exclude, *(qid for qid, _ in taken)],
                prefer_subchapters=prefer_subchapters, **where,
            )
            taken.extend((qid, same_chapter) for qid in found.question_ids)

        if chapters and difficulty in DIFFICULTY_ORDER:
            rank = DIFFICULTY_ORDER.index(difficulty)
            near = (d for d in DIFFICULTY_ORDER if d != difficulty and (allowed is None or d in allowed))
            for other in sorted(near, key=lambda d: abs(DIFFICULTY_ORDER.index(d) - rank)):
                await take(True, chapter_codes=chapters, difficulty=other)
        anywhere = None if allowed is None else sorted({*allowed, *([difficulty] if difficulty else [])})
        for level in ([difficulty, None] if difficulty else [None]):
            if scope:
                await take(False, chapter_codes=scope, difficulty=level, grade=grade, difficulties=anywhere)
            await take(False, chapter_codes=None, difficulty=level, grade=grade, difficulties=anywhere)
        return taken

    @staticmethod
    def _draft_text(draft: ExamDraft, structure: Structure) -> str:
        head = f"{draft.title}: BẢN NHÁP đề ôn (chưa chính thức, chờ em duyệt). Chưa kèm đáp án."
        if isinstance(structure, TemplatePreviewStructure):
            head += f" Theo mẫu \"{structure.template_name}\"."
        lines = [head]
        section = None
        for q in draft.items:
            if q.get("section_title") and q["section_title"] != section:
                section = q["section_title"]
                lines += ["", section]
            elif q["order"] == 1:
                lines.append("")
            lines.append(f"Câu {q['order']} [{q['code']} · {q.get('chapter') or '?'} · {q.get('difficulty') or '?'}] "
                         f"{q['content'].strip()}")
            for s in q["statements"]:
                lines.append(f"   - {s['content']}")
        want = structure.total
        if len(draft.items) < want or draft.shortages:
            lines += ["", f"Lưu ý: ngân hàng không đủ câu như yêu cầu. Mình chỉ đưa {len(draft.items)}/{want} câu có thật, "
                          f"thiếu {want - len(draft.items)} câu, không tự bịa thêm. "
                          + "; ".join(ExamChatUseCase._shortage_text(s) for s in draft.shortages)]
        return "\n".join(lines)

    @staticmethod
    def _shortage_text(s: dict) -> str:
        where = s.get("section_title") or s.get("chapter") or ""
        if s.get("section_title") and s.get("question_type"):
            where += f" ({TYPE_NAME[s['question_type']]})"
        level = DIFF_NAME[s["difficulty"]] if s.get("difficulty") else "mọi mức"
        return f"{where} {level}: chỉ có {s['available']}/{s['requested']} câu"
