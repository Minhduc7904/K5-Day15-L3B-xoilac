"""Luồng nghiệp vụ pipeline học sinh tạo đề ôn (issue #4).

Một phiên có tin nhắn và đúng một bản xem trước hiện tại. Học sinh chỉnh bản xem trước bằng chat (respond) hoặc
qua API (update_preview); cả hai cùng dùng luật ở exam_preview_rules và cùng kiểm version để không ghi đè nhau.
Chỉ sau khi xác nhận mới chọn câu từ ngân hàng đã duyệt để dựng đề nháp; đề nháp không có đáp án hay lời giải.

Hành vi bám codebase/agent.py (lát cắt đã đo): chặn trước, hỏi lại khi thiếu hoặc mâu thuẫn, không bịa câu.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.models.exam_chat import ExamChatSession, ExamDraft, ExamPreview
from app.repositories.exam_chat_repository import ExamChatRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.service.exam_chat_sources import ExamTemplateSource, StudentHistorySource
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
    new_structure,
)

MIN_ANSWERS = 5      # chương làm ít hơn số câu này không dùng để xếp hạng (như agent.py)
CLOSE_GAP = 0.10     # hai chương yếu nhất cách nhau ≤ 10 điểm % → chia câu cho cả hai
VN_TZ = timezone(timedelta(hours=7))
CHAPTER_PHRASE = re.compile(r"chuong\s+([a-z0-9 ]+?)(?:\s+cho\b|\s+\d|[,.;:!?(]|$)")


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

    # ---------- phiên ----------

    async def create_session(self, student_ref: str) -> ExamChatSession:
        return await self._repo.create_session(student_ref.strip())

    async def _session(self, session_id: int) -> ExamChatSession:
        item = await self._repo.get_session(session_id)
        if item is None:
            raise SessionNotFound()
        return item

    async def get_state(self, session_id: int):
        session = await self._session(session_id)
        messages = await self._repo.list_messages(session_id)
        preview = await self._repo.get_preview(session_id)
        draft = await self._repo.latest_draft(session_id)
        return session, messages, preview, draft

    async def get_preview(self, session_id: int) -> ExamPreview:
        await self._session(session_id)
        preview = await self._repo.get_preview(session_id)
        if preview is None:
            raise PreviewNotFound()
        return preview

    async def latest_draft(self, session_id: int) -> ExamDraft | None:
        await self._session(session_id)
        return await self._repo.latest_draft(session_id)

    # ---------- đường chỉnh qua API ----------

    async def update_preview(self, session_id: int, edit: PreviewEdit, expected_version: int) -> ExamPreview:
        preview = await self.get_preview(session_id)
        if preview.version != expected_version:
            raise VersionConflict(preview.version)
        structure = apply_edit(PreviewStructure.model_validate(preview.structure), edit)
        await self._validate(structure)
        return await self._repo.save_preview(
            session_id, {"structure": structure.model_dump(mode="json"), "status": "EDITED"}
        )

    async def confirm(self, session_id: int, expected_version: int) -> tuple[ExamPreview, ExamDraft | None, str]:
        preview = await self.get_preview(session_id)
        if preview.version != expected_version:
            raise VersionConflict(preview.version)
        if not can_confirm(preview.status):
            raise InvalidState(f"Bản xem trước đang ở trạng thái {preview.status}, chỉnh lại trước khi xác nhận.")
        return await self._confirm_and_build(session_id, preview)

    # ---------- đường chỉnh qua chat ----------

    async def respond(self, session_id: int, text: str) -> ChatTurn:
        session = await self._session(session_id)
        await self._repo.add_message(session_id, "student", text)
        turn = await self._decide(session, text)
        version = turn.preview.version if turn.preview is not None else None
        await self._repo.add_message(session_id, "assistant", turn.reply, version)
        return turn

    async def _decide(self, session: ExamChatSession, text: str) -> ChatTurn:
        intent = chat_intent.read(text)
        sid = session.session_id
        current = await self._repo.get_preview(sid)

        if intent.kind == "refuse":
            return ChatTurn(intent.text, notes=["chặn trước AI"])
        if intent.kind == "exam":
            return await self._exam_branch(intent.exam or {})
        if intent.asked_total is not None and intent.asked_total > MAX_TOTAL and intent.kind != "confirm":
            return ChatTurn(f"Một đề ôn tối đa {MAX_TOTAL} câu. Em chọn số câu nhỏ hơn nhé.")

        if intent.kind == "confirm":
            return await self._chat_confirm(sid, current, intent)
        if intent.kind == "edit":
            return await self._chat_edit(sid, current, intent.edit)

        unknown = await self._unknown_chapter(text, intent)
        if unknown:
            return ChatTurn(unknown, notes=["thu hẹp: chương không có trong ngân hàng"])
        if intent.kind == "weak":
            return await self._weak_branch(session, intent.edit)
        return ChatTurn("Em muốn ôn chương nào, hay để mình chọn theo chương em hay sai? " + chat_intent.OFFER)

    async def _exam_branch(self, exam: dict) -> ChatTurn:
        if not exam.get("exam_type"):
            return ChatTurn("Em muốn ôn theo kỳ thi nào: giữa kỳ hay cuối kỳ, học kỳ 1 hay 2, lớp mấy? "
                            "Hoặc thi tốt nghiệp THPT, HSA, TSA?")
        found = await self._templates.find(exam["exam_type"], exam.get("grade"), exam.get("version_label"))
        if not found:
            return ChatTurn("Mình chưa có cấu trúc đã xác thực nguồn cho kỳ thi này nên không nêu số câu hay phân bố "
                            "chương, để khỏi nói sai. " + chat_intent.OFFER, notes=["thu hẹp: chưa có mẫu đã duyệt"])
        if len(found) > 1:
            names = "; ".join(t.get("name", "") for t in found)
            return ChatTurn(f"Có {len(found)} mẫu đã duyệt phù hợp: {names}. Em cho mình biết thêm khối, học kỳ "
                            "hoặc năm để chọn đúng một mẫu nhé.")
        # Dựng đề theo mẫu kỳ thi cần hợp đồng #5 (phần, loại câu, ràng buộc): làm sau khi #5 merge.
        return ChatTurn(f"Mình tìm thấy mẫu đã duyệt \"{found[0].get('name', '')}\", nhưng chưa dựng đề theo mẫu kỳ thi "
                        "được. " + chat_intent.OFFER, notes=["nhánh kỳ thi: chờ #5"])

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
            sid, {"structure": structure.model_dump(mode="json"), "status": "EDITED", "mode": "CHAPTER"}
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
            sid, {"structure": structure.model_dump(mode="json"), "status": status, "mode": "CHAPTER"}
        )
        names = await self._bank.chapter_names()
        reply = "Đề xuất cấu trúc đề ôn (chưa tạo đề):\n" + describe(structure, names) + "\n" + self._ask_confirm()
        return ChatTurn(reply, preview=preview, preview_changed=True)

    async def _weak_branch(self, session: ExamChatSession, edit: PreviewEdit) -> ChatTurn:
        history = await self._history.get(session.student_ref)
        if history is None or not history.chapters:
            return ChatTurn(f"Mình chưa có lịch sử làm bài của {session.student_ref} nên chưa biết chương em hay sai, "
                            "và mình không đoán. Em muốn ôn chương nào?", notes=["dừng: chưa có lịch sử"])
        ranked = sorted((c for c in history.chapters if c.total >= MIN_ANSWERS), key=lambda c: (c.rate, c.code))
        if history.conflicting:
            lines = "\n".join(f"- {c.code}: đúng {c.correct}/{c.total} ({round(100 * c.rate)}%)" for c in ranked[:3])
            return ChatTurn(f"Kết quả làm bài của {session.student_ref} có chỗ mâu thuẫn (khoảng "
                            f"{round(100 * history.conflict_ratio)}% số câu vừa đúng vừa sai trong cùng một lượt), nên "
                            f"mình chưa xác định chắc chương yếu. Các chương đang thấp nhất:\n{lines}\n"
                            "Em muốn ôn chương nào trong số này, hay chương khác?", notes=["dừng: dữ liệu mâu thuẫn"])
        if not ranked:
            return ChatTurn("Em làm chưa đủ nhiều câu ở mỗi chương để mình xác định chương yếu. Em muốn ôn chương nào?")
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

    # ---------- dựng đề ----------

    async def _errors(self, structure: PreviewStructure) -> list[str]:
        names = await self._bank.chapter_names()
        return check_structure(structure, set(names) if names else None)

    async def _validate(self, structure: PreviewStructure) -> None:
        errors = await self._errors(structure)
        if errors:
            raise PreviewRuleError(errors)

    async def _confirm_and_build(self, sid: int, preview: ExamPreview) -> tuple[ExamPreview, ExamDraft | None, str]:
        structure = PreviewStructure.model_validate(preview.structure)
        await self._validate(structure)
        confirmed = await self._repo.save_preview(sid, {"status": "CONFIRMED"})
        chosen: list[int] = []
        shortages: list[dict] = []
        meta: dict[int, tuple[str, str]] = {}
        for code, mix in difficulty_plan(structure).items():
            for diff, k in mix.items():
                res = await self._bank.pick(code, diff, k, exclude=chosen)
                chosen += res.question_ids
                meta.update({q: (code, diff) for q in res.question_ids})
                if len(res.question_ids) < k:
                    shortages.append({"chapter": code, "difficulty": diff, "requested": k,
                                      "available": len(res.question_ids)})
        loaded = await self._bank.load_items(chosen)
        items = []
        for qid in chosen:
            if qid not in loaded:          # chặn sau: chỉ câu còn đọc được trong ngân hàng đã duyệt
                continue
            q = loaded[qid]
            items.append({"order": len(items) + 1, "chapter": meta[qid][0], **q})
        if not items:
            preview = await self._repo.save_preview(sid, {"status": "EDITED"})
            return preview, None, "Ngân hàng chưa có câu nào phù hợp cấu trúc này. Em thử đổi chương hoặc độ khó nhé."
        draft = await self._repo.add_draft({
            "session_id": sid,
            "preview_version": confirmed.version,
            "title": draft_title(),
            "structure": structure.model_dump(mode="json"),
            "items": items,
            "shortages": shortages,
        })
        preview = await self._repo.save_preview(sid, {"status": "BUILT"})
        return preview, draft, self._draft_text(draft, structure)

    @staticmethod
    def _draft_text(draft: ExamDraft, structure: PreviewStructure) -> str:
        lines = [f"{draft.title}: BẢN NHÁP đề ôn (chưa chính thức, chờ em duyệt). Chưa kèm đáp án.", ""]
        for q in draft.items:
            lines.append(f"Câu {q['order']} [{q['code']} · {q['chapter']} · {q['difficulty']}] {q['content'].strip()}")
            for s in q["statements"]:
                lines.append(f"   - {s['content']}")
        want = structure.total
        if len(draft.items) < want or draft.shortages:
            detail = "; ".join(f"{s['chapter']} {DIFF_NAME[s['difficulty']]}: chỉ có {s['available']}/{s['requested']} câu"
                               for s in draft.shortages)
            lines += ["", f"Lưu ý: ngân hàng không đủ câu như yêu cầu. Mình chỉ đưa {len(draft.items)}/{want} câu có thật, "
                          f"thiếu {want - len(draft.items)} câu, không tự bịa thêm. {detail}"]
        return "\n".join(lines)
