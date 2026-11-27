from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.study_time import STUDY_TZ
from app.models.student import StudentProfile, StudentStudyDay, StudyReminderDelivery
from app.models.user import ROLE_STUDENT, STATUS_ACTIVE, User

MAX_ATTEMPTS = 3
CLAIM_TIMEOUT = timedelta(minutes=2)


class StudyReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _eligible(self, day: date):
        return (
            select(StudentProfile, User)
            .join(User, User.user_id == StudentProfile.user_id)
            .join(StudentStudyDay, StudentStudyDay.user_id == StudentProfile.user_id)
            .where(
                StudentStudyDay.weekday == day.isoweekday(), StudentProfile.reminder_time.is_not(None),
                User.role == ROLE_STUDENT, User.status == STATUS_ACTIVE, User.email_verified_at.is_not(None),
            )
        )

    async def claim_one(self, now: datetime) -> int | None:
        local = now.astimezone(STUDY_TZ)
        day = local.date()
        delivery = StudyReminderDelivery
        query = (
            self._eligible(day)
            .outerjoin(delivery, and_(delivery.user_id == StudentProfile.user_id, delivery.local_date == day))
            .where(
                StudentProfile.reminder_time <= local.time(),
                or_(delivery.user_id.is_(None), and_(delivery.status == "pending", delivery.next_attempt_at <= now)),
            )
            .order_by(StudentProfile.user_id)
            .limit(1)
            .with_for_update(of=StudentProfile, skip_locked=True)
        )
        row = (await self._session.execute(query)).first()
        if row is None:
            return None
        profile, _ = row
        job = await self._session.get(delivery, (profile.user_id, day), with_for_update=True)
        # Re-read after locking: another worker may have claimed it between the join and the lock.
        if job is not None and job.status != "pending":
            return None
        scheduled_at = datetime.combine(day, profile.reminder_time, STUDY_TZ).astimezone(UTC)
        if job is None:
            job = delivery(user_id=profile.user_id, local_date=day, attempt_count=0)
            self._session.add(job)
        job.scheduled_at = scheduled_at
        job.status = "sending"
        job.claimed_at = now
        job.next_attempt_at = None
        return profile.user_id

    async def recipient(self, user_id: int, day: date, due_by: time) -> str | None:
        query = self._eligible(day).where(
            StudentProfile.user_id == user_id, StudentProfile.reminder_time <= due_by,
        )
        row = (await self._session.execute(query)).first()
        return row[1].email if row else None

    async def begin_attempt(self, user_id: int, day: date) -> int | None:
        job = await self._session.get(StudyReminderDelivery, (user_id, day), with_for_update=True)
        if job is None or job.status != "sending":
            return None
        job.attempt_count += 1
        return job.attempt_count

    async def finish(
        self, user_id: int, day: date, status: str, *, next_attempt_at: datetime | None = None,
        sent_at: datetime | None = None, message_id: str | None = None,
    ) -> None:
        await self._session.execute(
            update(StudyReminderDelivery)
            .where(
                StudyReminderDelivery.user_id == user_id, StudyReminderDelivery.local_date == day,
                StudyReminderDelivery.status == "sending",
            )
            .values(status=status, next_attempt_at=next_attempt_at, sent_at=sent_at, gmail_message_id=message_id)
        )

    async def settle_old_jobs(self, day: date, now: datetime) -> None:
        await self._session.execute(
            update(StudyReminderDelivery)
            .where(StudyReminderDelivery.local_date < day, StudyReminderDelivery.status == "pending")
            .values(status="expired", next_attempt_at=None)
        )
        await self._session.execute(
            update(StudyReminderDelivery)
            .where(
                StudyReminderDelivery.status == "sending",
                StudyReminderDelivery.claimed_at <= now - CLAIM_TIMEOUT,
            )
            .values(status="uncertain")
        )
