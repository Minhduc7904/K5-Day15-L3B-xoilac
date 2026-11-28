from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

KINDS = ("attempt_graded", "draft_ready", "credit_granted", "study_reminder")


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self, user_id: int, kind: str, title: str, *, dedupe_key: str, body: str = "", link: str | None = None,
        payload: dict | None = None,
    ) -> None:
        """Ghi thông báo trong giao dịch của nghiệp vụ đang chạy. Cùng `dedupe_key` thì bỏ qua, không lỗi."""
        insert = pg_insert if self.session.get_bind().dialect.name == "postgresql" else sqlite_insert
        await self.session.execute(
            insert(Notification).values(user_id=user_id, kind=kind, title=title, body=body, link=link,
                                         payload=payload, dedupe_key=dedupe_key)
            .on_conflict_do_nothing(index_elements=["user_id", "dedupe_key"])
        )

    async def recent(self, user_id: int, before_id: int | None, limit: int) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if before_id is not None:
            query = query.where(Notification.id < before_id)
        return list(await self.session.scalars(query.order_by(Notification.id.desc()).limit(limit)))

    async def unread_count(self, user_id: int) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        ) or 0

    async def mark_read(self, user_id: int, notification_id: int) -> bool:
        exists = await self.session.scalar(
            select(Notification.id).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        if exists is None:
            return False
        await self.session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
        return True

    async def mark_all_read(self, user_id: int) -> None:
        await self.session.execute(
            update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )

    async def latest_id(self) -> int:
        return await self.session.scalar(select(func.coalesce(func.max(Notification.id), 0))) or 0

    async def after(self, last_id: int, limit: int = 200) -> list[Notification]:
        return list(await self.session.scalars(
            select(Notification).where(Notification.id > last_id).order_by(Notification.id).limit(limit)
        ))

    async def commit(self) -> None:
        await self.session.commit()
