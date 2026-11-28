from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import StudentProfile, StudentStudyDay
from app.models.user import User


class StudentProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> StudentProfile | None:
        return await self._session.get(StudentProfile, user_id)

    async def get_with_days(self, user_id: int) -> tuple[StudentProfile | None, list[int]]:
        query = (
            select(StudentProfile, StudentStudyDay.weekday)
            .outerjoin(StudentStudyDay, StudentStudyDay.user_id == StudentProfile.user_id)
            .where(StudentProfile.user_id == user_id)
            .order_by(StudentStudyDay.weekday)
        )
        rows = (await self._session.execute(query)).all()
        if not rows:
            return None, []
        return rows[0][0], [day for _, day in rows if day is not None]

    async def save(self, user: User, values: dict, days: list[int], display_name: str | None) -> StudentProfile:
        # Lock even when this is the first save and the profile row does not exist.
        await self._session.execute(select(User.user_id).where(User.user_id == user.user_id).with_for_update())
        profile = await self.get(user.user_id)
        if profile is None:
            profile = StudentProfile(user_id=user.user_id, **values)
            self._session.add(profile)
            await self._session.flush()
        else:
            for field, value in values.items():
                setattr(profile, field, value)
            profile.updated_at = func.now()
        if display_name is not None:
            user.display_name = display_name
        await self._session.execute(delete(StudentStudyDay).where(StudentStudyDay.user_id == user.user_id))
        self._session.add_all(StudentStudyDay(user_id=user.user_id, weekday=day) for day in days)
        await self._session.commit()
        return profile
