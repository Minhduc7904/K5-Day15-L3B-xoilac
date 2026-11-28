from app.repositories.notifications import NotificationRepository


class NotFound(Exception):
    pass


class Notifications:
    def __init__(self, repo: NotificationRepository):
        self.repo = repo

    async def list(self, user_id: int, before_id: int | None, limit: int) -> dict:
        rows = await self.repo.recent(user_id, before_id, limit + 1)
        page = rows[:limit]
        return {"items": page, "unread": await self.repo.unread_count(user_id),
                "next_before_id": page[-1].id if len(rows) > limit else None}

    async def read(self, user_id: int, notification_id: int) -> None:
        if not await self.repo.mark_read(user_id, notification_id):
            raise NotFound()
        await self.repo.commit()

    async def read_all(self, user_id: int) -> None:
        await self.repo.mark_all_read(user_id)
        await self.repo.commit()
