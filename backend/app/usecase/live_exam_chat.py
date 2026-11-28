"""Authenticated, model-directed exam authoring with atomic draft and credit writes."""
import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.study_time import study_date
from app.models.exam_chat import ExamChatAttachment, ExamChatMessage, ExamDraft
from app.repositories.credits import CreditRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.student_profiles import StudentProfileRepository
from app.service.exam_chat_model import ChatAction, ExamChatModel, ExamChatModelError
from app.service.exam_chat_ocr import ExamChatImageError, ExamChatOcr, PreparedImage
from app.service.storage_service import StorageService
from app.usecase.exam_chapter_scope import expand_chapters, leaf_codes
from app.usecase.exam_chat import (
    ChatTurn, ExamChatUseCase, InvalidState, Requester, SessionNotFound,
    VersionConflict, draft_title, load_structure,
)
from app.usecase.exam_chat_intent import next_practice, norm, read, refusal
from app.usecase.exam_personalization import (
    PracticeRequest, practice_chapters, recommendation_context, review_text,
    validate_recommendation, weak_priority,
)
from app.usecase.exam_preview_rules import (
    DEFAULT_TOTAL, MAX_TOTAL, PreviewEdit, PreviewRuleError, PreviewStructure, allocate,
    apply_edit, ensure_valid, matrix_plan, new_structure,
)
from app.usecase.exam_scoring import allocate_points
from app.usecase.exam_template_plan import TemplateConflict, TemplatePreviewStructure, apply_template_edit, from_template


log = logging.getLogger(__name__)

EXAM_PERIOD = {"midterm_1": "GK1", "midterm_2": "GK2", "final_1": "CK1", "final_2": "CK2",
               "national_high_school": "THPT"}


class LiveExamChat(ExamChatUseCase):
    def __init__(self, session: AsyncSession, model: ExamChatModel, ocr: ExamChatOcr, storage: StorageService, *args) -> None:
        super().__init__(*args)
        self.db = session
        self.model = model
        self.ocr = ocr
        self.storage = storage

    async def _lock(self, sid: int, requester: Requester | None):
        session = await self._repo.lock_session(sid)
        if requester is None or session is None or session.deleted_at is not None or session.user_id != requester.user_id:
            raise SessionNotFound()
        return session

    async def _stage(self, sid, structure, current, *, reason=None, operation=None):
        if structure.total > MAX_TOTAL:
            raise PreviewRuleError(["Mỗi đề tối đa 50 câu."])
        original = (current.original_structure or current.structure) if current else structure.model_dump(mode="json")
        preview = await self._repo.save_preview(sid, {
            "structure": structure.model_dump(mode="json"), "mode": structure.kind,
            "status": "EDITED" if current else "PROPOSED", "reason": reason,
            "operation": operation, "offer": None, "original_structure": original,
        }, commit=False)
        return ChatTurn(f"Đề xuất cấu trúc gồm {structure.total} câu. Em xem lại rồi xác nhận để dựng đề nhé.",
                        preview=preview, preview_changed=True)

    async def update_preview(self, session_id, edit, expected_version, requester=None):
        await self._lock(session_id, requester)
        preview = await self.get_preview(session_id, requester)
        if preview.version != expected_version or preview.status == "CANCELLED":
            raise VersionConflict(preview.version)
        structure = await self._edited(load_structure(preview), edit)
        result = await self._stage(session_id, structure, preview, reason=preview.reason)
        await self.db.commit()
        return result.preview

    async def _edited(self, structure, edit):
        if not isinstance(structure, PreviewStructure):
            if edit.rows is not None or edit.type_counts is not None or edit.duration_minutes is not None:
                raise TemplateConflict(["Mẫu kỳ thi giữ nguyên dạng câu, thời lượng và phân bố."])
            result = apply_template_edit(structure, edit.model_copy(update={"chapter_codes": None}))
            if result.total > MAX_TOTAL:
                raise TemplateConflict(["Mẫu này vượt 50 câu. Hãy chọn mẫu khác hoặc tạo đề tự chọn."])
            if edit.chapter_codes:
                catalog = await self._bank.chapter_catalog()
                parents = {code: entry["parent_code"] for code, entry in catalog.items()}
                if any(code not in parents for code in edit.chapter_codes):
                    raise TemplateConflict(["Có chương không nằm trong danh mục."])
                wanted = list(dict.fromkeys(leaf for code in edit.chapter_codes for leaf in leaf_codes(code, parents)))
                unrestricted = any(section.allowed_chapters is None for section in result.sections)
                allowed = {leaf for section in result.sections for code in section.allowed_chapters or []
                           for leaf in leaf_codes(code, parents)}
                if any((not unrestricted and code not in allowed)
                       or (result.grade and int(code[:2]) > result.grade) for code in wanted):
                    raise TemplateConflict(["Có chương ngoài phạm vi của mẫu kỳ thi."])
                for section in result.sections:
                    scope = {leaf for code in section.allowed_chapters or [] for leaf in leaf_codes(code, parents)}
                    selected = [code for code in wanted if section.allowed_chapters is None or code in scope]
                    section.chapters = selected or None
            return result
        catalog = await self._bank.chapter_catalog()
        codes = set(edit.chapter_codes or []) | set(edit.chapter_counts or {})
        if codes - catalog.keys():
            raise PreviewRuleError(["Có chương không nằm trong danh mục."])
        result = apply_edit(structure, edit)
        ensure_valid(result, set(catalog))
        result = expand_chapters(result, {code: entry["parent_code"] for code, entry in catalog.items()})
        if result.type_counts is None:
            result.type_counts = {"SINGLE_CHOICE": result.total}
        ensure_valid(result, set(catalog))
        result.rows = matrix_plan(result)
        return result

    async def _context(self, sid, requester, text, version, *, image_turn=False):
        session = await self._session(sid, requester)
        current = await self._repo.get_preview(sid)
        draft = await self._repo.latest_draft(sid)
        profile = await StudentProfileRepository(self.db).get(requester.user_id)
        transcript = await self._repo.transcript(sid)
        messages = [{"id": m.message_id, "role": m.role, "text": m.content} for m in transcript]
        latest = messages[-1]["id"] if messages else 0
        cutoff = session.summarized_through or 0
        summary = session.context_summary or ""
        current_version = current.version if current else None
        visible_version = current_version if current and current.status != "CANCELLED" else None
        if version is not None and version != (visible_version or 0):
            raise VersionConflict(current_version)
        context = {
            "request": text,
            "student": {"grade": profile.grade, "target_score": profile.target_score,
                        "exam_type": EXAM_PERIOD.get(profile.exam_period)} if profile else {},
            "catalog": await self._bank.chapter_catalog(),
            "preview": current.structure if current and current.status != "CANCELLED" else None,
            "preview_status": current.status if current else None,
            "original_structure": current.original_structure if current else None,
            "pending_operation": current.operation if current else None,
            "pending_shortage": {k: v for k, v in current.offer.items() if k != "ids"}
            if current and current.offer else None,
            "draft": {"structure": draft.structure,
                      "questions": [{k: item.get(k) for k in ("order", "code", "chapter", "difficulty", "type")}
                                    for item in draft.items]} if draft else None,
        }
        await self.db.rollback()
        pending = [message for message in messages if message["id"] > cutoff]
        older = pending[:-16] if len(pending) > 32 else []
        previous_summary = summary
        try:
            for start in range(0, len(older), 24):
                summary = await self.model.summarize(summary, older[start:start + 24])
            if older:
                cutoff = older[-1]["id"]
        except ExamChatModelError:
            if not image_turn:
                raise
            summary = previous_summary
            older = []
        words = {word for word in text.casefold().split() if len(word) >= 4}
        previous = [message for message in messages if message["id"] <= cutoff]
        related = sorted(previous, key=lambda message: len(words & set(message["text"].casefold().split())),
                         reverse=True)[:4] if words else []
        context.update(summary=summary, recent=pending[len(older):][-32:], past_references=related)
        return context, latest, current_version, summary, cutoff

    async def _interpret_images(self, images: list[PreparedImage], context: dict) -> tuple[ChatAction | None, str]:
        try:
            texts = await self.ocr.recognize(images)
            evidence = await self.model.screen_ocr(texts, context.get("image_purpose"))
            if not evidence:
                reason = ("Mình chưa đọc đủ chữ Toán trong ảnh." if not any(texts) else
                          "Mình chưa xác minh được nội dung ảnh phù hợp để tạo đề ôn Toán THPT.")
                hint = ("Em gửi ảnh ma trận rõ hơn hoặc nhập số câu theo từng chương nhé."
                        if context.get("image_purpose") == "matrix"
                        else "Em gửi ảnh rõ hơn hoặc nhập chủ đề muốn ôn nhé.")
                return None, reason + " " + hint
            context["ocr_evidence"] = evidence
            action = await self.model.interpret(context)
        except ExamChatImageError as exc:
            return None, str(exc)
        except ExamChatModelError:
            return None, "Ảnh đã được lưu. Mình chưa kiểm tra được nội dung ảnh, em thử lại sau nhé."

        if action.action == "confirm":
            return None, "Ảnh dùng để chọn chủ đề ôn. Em xác nhận bản xem trước bằng một tin nhắn riêng hoặc nút Dựng đề nhé."
        if not context["request"] and action.action not in {"chapter", "clarify", "unsupported"}:
            return None, "Em muốn tạo đề ôn theo chủ đề Toán trong ảnh, hay muốn chỉ định chương cụ thể?"
        ignored = len(images) - len(evidence)
        notice = f"Mình chỉ dùng ảnh đọc được và phù hợp với Toán THPT. Đã bỏ qua {ignored} ảnh." if ignored else ""
        catalog = context["catalog"]
        named = [catalog[code]["name"] for code in dict.fromkeys([*action.chapters, *action.chapter_counts])
                 if code in catalog]
        if named and action.action == "chapter":
            source = ("ma trận trong ảnh" if any(item.get("kind") == "matrix" for item in evidence)
                      else "nội dung ảnh")
            found = f"Từ {source}, mình thấy các chương: {', '.join(named)}."
            notice = f"{notice}\n{found}" if notice else found
        return action, notice

    async def respond(self, session_id: int, text: str, requester=None, *, version=None, images=None, plan=None,
                      image_purpose=None) -> ChatTurn:
        if requester is None:
            raise SessionNotFound()
        prepared = self.ocr.prepare(images) if images else []
        started = perf_counter()
        context, latest, previous_version, summary, cutoff = await self._context(
            session_id, requester, text, version, image_turn=bool(prepared),
        )
        if plan is not None:
            context["student_plan"] = plan.model_dump(mode="json", exclude_defaults=True)
        if prepared and image_purpose:
            context["image_purpose"] = image_purpose
        normalized = norm(text)
        blocked = refusal(normalized)
        next_exam = next_practice(normalized) if not prepared else None
        if blocked:
            action, notice = None, blocked
        elif prepared:
            action, notice = await self._interpret_images(prepared, context)
        elif next_exam:
            if next_exam.asked_total is not None and not 1 <= next_exam.asked_total <= MAX_TOTAL:
                action, notice = None, f"Mỗi đề cần từ 1 đến {MAX_TOTAL} câu."
            else:
                action = ChatAction(action="history", total=next_exam.edit.total,
                                    difficulty_counts=next_exam.edit.difficulty_counts or {})
                notice = ""
        else:
            try:
                action, notice = await self.model.interpret(context), ""
            except ExamChatModelError:
                if read(text).kind != "weak":
                    raise
                action, notice = None, "AI đang bận. Em thử lại hoặc chọn một chương để ôn nhé."
        proposal = None
        if action and action.action == "history":
            try:
                proposal = await self._recommend(requester, action, context)
            except PreviewRuleError as exc:
                proposal = (None, " ".join(exc.errors))
        log.info("exam_chat action=%s image_count=%d model_latency_ms=%d",
                 action.action if action else "image_notice", len(prepared), (perf_counter() - started) * 1000)
        session = await self._lock(session_id, requester)
        current = await self._repo.get_preview(session_id)
        current_version = current.version if current else None
        if current_version != previous_version or await self._repo.transcript(session_id, latest):
            raise VersionConflict(current_version)
        try:
            if proposal:
                structure, reply = proposal
                turn = (await self._stage(session_id, structure, current, reason="Theo lịch sử làm bài đã chấm.")
                        if structure else ChatTurn(reply))
                if structure:
                    turn.reply = reply + "\n" + turn.reply
            else:
                turn = await self._dispatch(session_id, requester, current, action, context) if action else ChatTurn(notice)
        except PreviewRuleError as exc:
            turn = ChatTurn(" ".join(exc.errors))
        if action and notice:
            turn.reply = notice + "\n" + turn.reply
        session.context_summary = summary or None
        session.summarized_through = cutoff or None
        await self._commit_turn(session_id, session, text, turn, prepared)
        return turn

    async def _recommend(self, requester: Requester, action: ChatAction, context):
        catalog = context["catalog"]
        if not (action.grade or action.chapters or action.chapter_counts):
            action = action.model_copy(update={"grade": context["student"].get("grade")})
        request = PracticeRequest.from_action(action, catalog)
        history = await self._history.get(requester.student_ref, grade=action.grade, chapter_codes=request.scope)
        if not (action.grade or request.scope) and history:
            return None, "Em chọn khối lớp hoặc chương muốn ôn để mình đọc đúng phạm vi bài đã làm nhé."
        review = review_text(history, catalog)
        if history is None or history.conflicting or not any(row.total for row in history.chapters):
            return None, review + "\nEm muốn chọn chương nào hoặc làm một bài ngắn để có thêm dữ liệu?"
        options, available = await self._bank.practice_capacity(
            practice_chapters(history, request, catalog), request.difficulties, request.types,
        )
        if available < request.total:
            return None, (review + f"\nKho có {available}/{request.total} câu phù hợp phạm vi và mức đã chọn. "
                          f"Còn thiếu {request.total - available} câu. Em giảm số câu hoặc đổi chương, mức độ nhé.")
        priority = weak_priority(history, options, catalog)
        unavailable = [catalog[row.code]["name"] for row in history.chapters if row.classification == "weak"
                       and not any((catalog[cell["chapter_code"]]["parent_code"] or cell["chapter_code"]) == row.code
                                   for cell in options)]
        if unavailable:
            review += "\nKho chưa có câu phù hợp để củng cố " + ", ".join(unavailable) + "."
        await self.db.rollback()
        try:
            model_input = recommendation_context(history, request, catalog, options, priority)
            recommendation = await self.model.recommend(model_input)
            structure, reasons = validate_recommendation(
                recommendation, history, request, catalog, model_input["bank"], priority,
            )
        except ExamChatModelError as exc:
            log.info("exam_chat recommendation unavailable reason=%s", exc)
            return None, review + "\nAI đang bận. Em thử lại hoặc chọn một chương để ôn nhé."
        except PreviewRuleError as exc:
            log.info("exam_chat recommendation rejected")
            return None, review + "\n" + " ".join(exc.errors) + " Em có thể đổi số câu hoặc mức độ rồi thử lại."
        chosen, _, shortages = await self._pick_chapters(structure)
        if shortages or len(chosen) != structure.total:
            details = "\n".join(self._shortage_text(shortage) for shortage in shortages)
            return None, (review + f"\nMa trận chỉ ghép được {len(chosen)}/{structure.total} câu phân biệt. "
                          "Em giảm số câu hoặc đổi mức độ nhé.\n" + details).rstrip()
        log.info("exam_chat recommendation accepted groups=%d question_count=%d", len(reasons), structure.total)
        return structure, "\n".join([review, *reasons])

    async def _commit_turn(self, sid, session, text, turn, images):
        attachments = []
        try:
            for index, image in enumerate(images, 1):
                key = f"exam-chat/{uuid4().hex}"
                attachments.append(ExamChatAttachment(position=index, mime_type=image.mime, object_key=key))
                try:
                    await self.storage.put(key, image.data, image.mime)
                except Exception as exc:
                    raise ExamChatImageError(503, "IMAGE_STORAGE_UNAVAILABLE",
                                             "Chưa lưu được ảnh. Em thử gửi lại nhé.") from exc
            self._write_messages(sid, session, text, turn, attachments=attachments)
            await self.db.flush()
        except BaseException:
            await self.db.rollback()
            for attachment in attachments:
                try:
                    await self.storage.delete(attachment.object_key)
                except Exception:
                    log.warning("exam_chat could not clean up an uncommitted image")
            raise
        # After commit is attempted, retain objects even if the connection drops and its outcome is unknown.
        await self.db.commit()

    def _write_messages(self, sid, session, text, turn, *, attachments=None):
        if text or attachments:
            message = ExamChatMessage(session_id=sid, role="student", content=text)
            if attachments:
                message.attachments = attachments
            self.db.add(message)
        self.db.add(ExamChatMessage(session_id=sid, role="assistant", content=turn.reply,
                                    preview_version=turn.preview.version if turn.preview else None))
        session.updated_at = datetime.now(timezone.utc)

    async def _dispatch(self, sid, requester, current, action: ChatAction, context):
        kind = action.action
        if kind == "unsupported":
            return ChatTurn("Mình chỉ hỗ trợ tạo và chỉnh đề ôn Toán từ ngân hàng đã duyệt.")
        if kind == "clarify":
            return ChatTurn(action.question or "Em muốn ôn chương nào hoặc theo mẫu kỳ thi nào?")
        if kind == "template":
            student = context["student"]
            exam_type = action.exam_type or student.get("exam_type")
            grade = action.grade or (student.get("grade") if exam_type in {"GK1", "GK2", "CK1", "CK2"} else None)
            if not exam_type:
                return ChatTurn("Em muốn ôn theo kỳ thi nào?")
            found = await self._templates.find(exam_type, grade, action.version_label)
            if len(found) != 1:
                options = "\n".join("- " + self._template_label(item) for item in found[:12])
                return ChatTurn("Có nhiều mẫu phù hợp. Em chọn khối hoặc năm nhé.\n" + options if found else
                                "Chưa có mẫu đã duyệt phù hợp. Em có muốn tạo đề tự chọn theo chương không?")
            structure = from_template(found[0])
            if structure.total > MAX_TOTAL:
                return ChatTurn("Mẫu đã duyệt có hơn 50 câu. Em chọn mẫu khác hoặc tạo đề tự chọn tối đa 50 câu nhé.")
            if action.chapters:
                structure = await self._edited(structure, PreviewEdit(chapter_codes=action.chapters))
            return await self._stage(sid, structure, current, reason=f"Theo mẫu {structure.template_name}")
        if kind == "chapter" or (kind == "edit" and context["preview"] is None and action.chapters):
            if not action.chapters and not action.chapter_counts:
                return ChatTurn("Em muốn ôn chương hoặc chủ đề nào?")
            total = (action.total or sum(action.chapter_counts.values()) or sum(action.type_counts.values())
                     or sum(action.difficulty_counts.values()) or DEFAULT_TOTAL)
            if not 1 <= total <= MAX_TOTAL:
                raise PreviewRuleError(["Mỗi đề cần từ 1 đến 50 câu."])
            codes = action.chapters or list(action.chapter_counts)
            if set(codes) - context["catalog"].keys():
                raise PreviewRuleError(["Em chọn chương có trong danh mục nhé."])
            structure = new_structure(allocate(total, dict.fromkeys(codes, 1)))
            structure = await self._edited(structure, self._action_edit(action, include_chapters=False))
            return await self._stage(sid, structure, current, reason="Theo yêu cầu ôn tập của em.")
        if not current or current.status == "CANCELLED":
            return ChatTurn("Phiên này chưa có cấu trúc đề. Em muốn ôn chương nào hoặc theo mẫu nào?")
        structure = load_structure(current)
        draft = await self._repo.latest_draft(sid)
        if kind in {"edit", "rebalance"}:
            if kind == "rebalance" and isinstance(structure, PreviewStructure):
                structure = structure.model_copy(update={"rows": None})
            structure = await self._edited(structure, self._action_edit(action))
            return await self._stage(sid, structure, current, reason=current.reason)
        if kind == "restore":
            original = current.original_structure or current.structure
            restored = (PreviewStructure.model_validate(original) if original.get("kind") != "EXAM_TEMPLATE"
                        else TemplatePreviewStructure.model_validate(original))
            return await self._stage(sid, restored, current)
        if kind == "cancel":
            if draft:
                preview = await self._repo.save_preview(sid, {
                    "structure": draft.structure, "mode": draft.structure["kind"], "status": "BUILT",
                    "operation": None, "offer": None,
                }, commit=False)
            else:
                await self._repo.save_preview(sid, {"status": "CANCELLED", "operation": None, "offer": None},
                                              commit=False)
                preview = None
            return ChatTurn("Đã bỏ thay đổi chưa xác nhận.", preview=preview, preview_changed=True)
        if kind == "view":
            return ChatTurn(f"Cấu trúc hiện tại có {structure.total} câu.", preview=current, preview_changed=True)
        if kind == "confirm":
            if current.status == "BUILT":
                return ChatTurn("Đề của phiên này đã được dựng. Em có thể xem hoặc yêu cầu đổi câu.", draft=draft)
            return await self._build(sid, requester, current, action.accepted_count)
        if not draft:
            return ChatTurn("Em cần dựng đề lần đầu trước khi đổi câu.")
        positions = sorted(set(action.question_orders))
        if kind == "replace" and (not positions or any(i < 1 or i > len(draft.items) for i in positions)):
            return ChatTurn(f"Em muốn đổi câu số mấy trong {len(draft.items)} câu hiện tại?")
        if kind in {"replace", "regenerate"}:
            if current.status != "BUILT":
                return ChatTurn("Phiên đang có chỉnh sửa chưa chốt. Em xác nhận hoặc hủy chỉnh sửa trước khi đổi câu nhé.")
            return await self._stage(sid, structure, current, reason=current.reason,
                                     operation={"kind": kind, "positions": positions})
        return ChatTurn("Em muốn tạo hay chỉnh đề theo cách nào?")

    @staticmethod
    def _action_edit(action, *, include_chapters=True):
        return PreviewEdit(chapter_codes=(action.chapters or None) if include_chapters else None, total=action.total,
                           chapter_counts=action.chapter_counts or None,
                           difficulty_counts=action.difficulty_counts or None, type_counts=action.type_counts or None,
                           duration_minutes=action.duration_minutes)

    async def confirm(self, session_id, expected_version, requester=None, *, accepted_count=None):
        session = await self._lock(session_id, requester)
        current = await self.get_preview(session_id, requester)
        draft = await self._repo.latest_draft(session_id)
        if current.status == "BUILT" and draft and draft.preview_version == expected_version:
            await self.db.commit()
            return current, draft, "Đề đã được lưu."
        if current.version != expected_version:
            raise VersionConflict(current.version)
        if current.status not in {"PROPOSED", "EDITED"}:
            raise InvalidState("Hãy mở bản xem trước hợp lệ trước khi xác nhận.")
        turn = await self._build(session_id, requester, current, accepted_count)
        self._write_messages(session_id, session, "Xác nhận cấu trúc đề", turn)
        await self.db.commit()
        return turn.preview, turn.draft, turn.reply

    async def _build(self, sid, requester, preview, accepted_count):
        structure = load_structure(preview)
        if structure.total > MAX_TOTAL:
            raise PreviewRuleError(["Mỗi đề tối đa 50 câu."])
        previous = await self._repo.latest_draft(sid)
        operation = preview.operation or {}
        if operation and previous:
            items, shortages = await self._replacement(previous, structure, operation)
            if not items or (shortages and all(a["question_id"] == b["question_id"]
                                              for a, b in zip(items, previous.items))):
                return ChatTurn("Kho chưa có câu thay thế phù hợp. Mình giữ nguyên đề hiện tại.",
                                preview=preview, preview_changed=True)
            requested = len(previous.items)
        else:
            if isinstance(structure, PreviewStructure):
                ensure_valid(structure, set(await self._bank.chapter_names()))
                chosen, meta, shortages = await self._pick_chapters(structure)
            else:
                chosen, meta, shortages = await self._pick_template(structure, prefer_subchapters=True)
            loaded = await self._bank.load_items(chosen)
            items = []
            for qid in chosen:
                if qid not in loaded:
                    continue
                data = {**loaded[qid], **meta[qid]}
                data.setdefault("chapter", next(iter(data["subchapter_codes"] or data["chapter_codes"]), None))
                items.append({"order": len(items) + 1, **data})
            requested = structure.total
        log.info("exam_chat build requested=%d selected=%d shortage_cells=%d", requested, len(items), len(shortages))
        if not items:
            return ChatTurn("Kho chưa có câu phù hợp. Em hãy chỉnh cấu trúc rồi thử lại.",
                            preview=preview, preview_changed=True)
        offer = {"requested": requested, "count": len(items), "shortages": shortages,
                 "ids": [item["question_id"] for item in items]}
        if (len(items) < requested or operation and shortages) and (
            preview.offer != offer or accepted_count != len(items)
        ):
            if preview.offer != offer:
                preview = await self._repo.save_preview(sid, {"offer": offer}, commit=False)
            message = (f"Kho chỉ có {len(items)}/{requested} câu phù hợp." if len(items) < requested else
                       f"Kho chỉ đổi được {len(operation.get('positions') or items) - len(shortages)} câu; "
                       "các câu còn thiếu phương án thay thế sẽ được giữ nguyên.")
            return ChatTurn(message + f" Em xác nhận dùng đề {len(items)} câu này nhé.",
                            preview=preview, preview_changed=True)
        items = allocate_points(items, structure.model_dump(mode="json"))
        if not previous:
            await CreditRepository(self.db).charge_exam(requester.user_id, sid, study_date(datetime.now(timezone.utc)))
        draft = previous or ExamDraft(session_id=sid)
        draft.preview_version = preview.version
        draft.title = getattr(structure, "title", None) or (previous.title if previous else draft_title())
        draft.structure = structure.model_dump(mode="json")
        draft.items = items
        draft.shortages = shortages if not operation else previous.shortages
        self.db.add(draft)
        await self.db.flush()
        if not previous:
            await NotificationRepository(self.db).add(
                requester.user_id, "draft_ready", "Đề nháp đã sẵn sàng", body=f"{draft.title}: {len(items)} câu.",
                link=f"/exams/draft-{draft.draft_id}", dedupe_key=f"draft:{draft.draft_id}",
                payload={"draft_id": draft.draft_id},
            )
        preview = await self._repo.save_preview(sid, {"status": "BUILT", "offer": None, "operation": None}, commit=False)
        return ChatTurn(f"Đã lưu đề {len(items)} câu. " + ("Lần tạo này đã trừ 100 credit." if not previous else
                        "Chỉnh đề miễn phí."), preview=preview, preview_changed=True, draft=draft)

    async def _replacement(self, draft, structure, operation):
        items = [dict(item) for item in draft.items]
        positions = set(operation["positions"] or range(1, len(items) + 1))
        used = [item["question_id"] for item in items]
        shortages: list[dict[str, Any]] = []
        for item in items:
            if item["order"] not in positions:
                continue
            section = next((s for s in getattr(structure, "sections", []) if s.order == item.get("section_order")), None)
            scope = section.effective_chapters() if section else [item["chapter"]] if item.get("chapter") else None
            difficulty = item["difficulty"] if not section or section.difficulty_distribution else None
            result = await self._bank.pick_for_section(
                question_type=item["type"], n=1, chapter_codes=scope, difficulty=difficulty,
                grade=getattr(structure, "grade", None), exclude=used, prefer_subchapters=True,
            )
            loaded = await self._bank.load_items(result.question_ids)
            if not loaded:
                shortages.append({"chapter": item.get("chapter"), "difficulty": difficulty, "requested": 1,
                                  "available": 0, "question_type": item["type"], "section_order": item.get("section_order")})
                continue
            new = next(iter(loaded.values()))
            used.append(new["question_id"])
            item.update(new, chapter=(item.get("chapter") if not section else next(iter(new["subchapter_codes"] or new["chapter_codes"]), None)))
        return items, shortages
