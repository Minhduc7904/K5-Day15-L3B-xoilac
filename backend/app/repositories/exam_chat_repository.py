from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam_chat import ExamChatMessage, ExamChatSession, ExamDraft, ExamPreview


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

    async def list_messages(self, session_id: int, limit: int = 200) -> Sequence[ExamChatMessage]:
        result = await self._session.execute(
            select(ExamChatMessage)
            .where(ExamChatMessage.session_id == session_id)
            .order_by(ExamChatMessage.message_id)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_preview(self, session_id: int) -> ExamPreview | None:
        return await self._session.get(ExamPreview, session_id)

    async def save_preview(self, session_id: int, values: dict[str, Any]) -> ExamPreview:
        """Tạo hoặc thay bản xem trước của phiên; tăng version mỗi lần ghi."""
        item = await self.get_preview(session_id)
        if item is None:
            item = ExamPreview(session_id=session_id, version=1, **values)
            self._session.add(item)
        else:
            for key, value in values.items():
                setattr(item, key, value)
            item.version = item.version + 1
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def add_draft(self, values: dict[str, Any]) -> ExamDraft:
        item = ExamDraft(**values)
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    async def latest_draft(self, session_id: int) -> ExamDraft | None:
        result = await self._session.execute(
            select(ExamDraft).where(ExamDraft.session_id == session_id).order_by(ExamDraft.draft_id.desc()).limit(1)
        )
        return result.scalars().first()
