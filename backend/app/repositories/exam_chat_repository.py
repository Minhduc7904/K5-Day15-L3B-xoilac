from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import noload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_chat import ExamChatAttachment, ExamChatMessage, ExamChatSession, ExamDraft, ExamPreview
from app.repositories.notifications import NotificationRepository
from app.repositories.pdf_imports import media


class ExamChatRepository:
    """Chỉ truy cập DB cho phiên chat, tin nhắn, bản xem trước, đề nháp. Không chứa luật nghiệp vụ."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, student_ref: str, user_id: int | None = None) -> ExamChatSession:
        item = ExamChatSession(student_ref=student_ref, user_id=user_id)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def get_session(self, session_id: int) -> ExamChatSession | None:
        return await self._session.get(ExamChatSession, session_id)

    async def add_message(
        self, session_id: int, role: str, content: str, preview_version: int | None = None
    ) -> ExamChatMessage:
        item = ExamChatMessage(session_id=session_id, role=role, content=content, preview_version=preview_version)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def list_sessions(self, user_id: int):
        first_message = (
            select(ExamChatMessage.content).where(
                ExamChatMessage.session_id == ExamChatSession.session_id, ExamChatMessage.role == "student",
            ).order_by(ExamChatMessage.message_id).limit(1).scalar_subquery()
        )
        query = (select(ExamChatSession, first_message)
                 .where(ExamChatSession.user_id == user_id, ExamChatSession.deleted_at.is_(None))
                 .order_by(ExamChatSession.updated_at.desc(), ExamChatSession.session_id.desc()))
        return (await self._session.execute(query)).all()

    async def rename_session(self, session: ExamChatSession, title: str) -> None:
        session.title = title
        await self._session.commit()

    async def hide_session(self, session: ExamChatSession) -> None:
        """Ẩn khỏi danh sách đoạn chat. Đề nháp của phiên vẫn còn để "Đề của tôi" và lượt làm bài dùng tiếp."""
        session.deleted_at = func.now()
        await self._session.commit()

    async def message_page(self, session_id: int, before: int | None, limit: int):
        query = select(ExamChatMessage).where(ExamChatMessage.session_id == session_id)
        if before is not None:
            query = query.where(ExamChatMessage.message_id < before)
        rows = (await self._session.scalars(query.order_by(ExamChatMessage.message_id.desc()).limit(limit))).all()
        return list(reversed(rows))

    def _owned_drafts(self, user_id: int):
        return (select(ExamDraft).join(ExamChatSession, ExamChatSession.session_id == ExamDraft.session_id)
                .where(ExamChatSession.user_id == user_id, ExamDraft.is_current))

    async def list_drafts(self, user_id: int):
        query = self._owned_drafts(user_id).order_by(ExamDraft.draft_id.desc())
        return (await self._session.scalars(query)).all()

    async def draft_by_id(self, user_id: int, draft_id: int):
        return await self._session.scalar(self._owned_drafts(user_id).where(ExamDraft.draft_id == draft_id))

    async def chat_attachment(self, session_id: int, attachment_id: int) -> tuple[str, str] | None:
        query = (select(ExamChatAttachment.object_key, ExamChatAttachment.mime_type)
                 .join(ExamChatMessage, ExamChatMessage.message_id == ExamChatAttachment.message_id)
                 .where(ExamChatMessage.session_id == session_id,
                        ExamChatAttachment.attachment_id == attachment_id))
        row = (await self._session.execute(query)).one_or_none()
        return (row.object_key, row.mime_type) if row else None

    async def media_key(self, media_id: int):
        return await self._session.scalar(select(media.c.object_key).where(media.c.media_id == media_id))

    async def lock_session(self, session_id: int) -> ExamChatSession | None:
        return await self._session.scalar(
            select(ExamChatSession).where(ExamChatSession.session_id == session_id)
            .with_for_update().execution_options(populate_existing=True)
        )

    async def transcript(self, session_id: int, after: int = 0):
        return (await self._session.scalars(
            select(ExamChatMessage).options(noload(ExamChatMessage.attachments))
            .where(ExamChatMessage.session_id == session_id, ExamChatMessage.message_id > after)
            .order_by(ExamChatMessage.message_id)
        )).all()

    async def list_messages(self, session_id: int, limit: int = 200) -> Sequence[ExamChatMessage]:
        return await self.message_page(session_id, None, limit)

    async def get_preview(self, session_id: int) -> ExamPreview | None:
        return await self._session.get(ExamPreview, session_id)

    async def save_preview(self, session_id: int, values: dict[str, Any], *, commit: bool = True) -> ExamPreview:
        """Tạo hoặc thay bản xem trước của phiên; tăng version mỗi lần ghi."""
        item = await self.get_preview(session_id)
        if item is None:
            item = ExamPreview(session_id=session_id, version=1, **values)
            self._session.add(item)
        else:
            for key, value in values.items():
                setattr(item, key, value)
            item.version = item.version + 1
        await (self._session.commit() if commit else self._session.flush())
        await self._session.refresh(item)
        return item

    async def add_draft(self, values: dict[str, Any]) -> ExamDraft:
        await self._session.execute(update(ExamDraft).where(ExamDraft.session_id == values["session_id"], ExamDraft.is_current).values(is_current=False))
        item = ExamDraft(**values)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def notify_draft_ready(self, session_id: int, draft: ExamDraft) -> None:
        """Thông báo đề mới cho chủ phiên (nhánh dựng không dùng model). Phiên không có chủ thì bỏ qua."""
        chat = await self._session.get(ExamChatSession, session_id)
        if chat is None or chat.user_id is None:
            return
        await NotificationRepository(self._session).add(
            chat.user_id, "draft_ready", "Đề nháp đã sẵn sàng", body=f"{draft.title}: {len(draft.items)} câu.",
            link=f"/exams/draft-{draft.draft_id}", dedupe_key=f"draft:{draft.draft_id}",
            payload={"draft_id": draft.draft_id},
        )
        await self._session.commit()

    async def latest_draft(self, session_id: int) -> ExamDraft | None:
        result = await self._session.execute(
            select(ExamDraft).where(ExamDraft.session_id == session_id, ExamDraft.is_current).order_by(ExamDraft.draft_id.desc()).limit(1)
        )
        return result.scalars().first()
