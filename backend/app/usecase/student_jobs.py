from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.study_time import STUDY_TZ, study_date
from app.repositories.credits import CREDIT_LIMIT, DAILY_CREDITS, CreditRepository
from app.repositories.study_reminders import MAX_ATTEMPTS, StudyReminderRepository
from app.service.email_service import (
    EmailConfigurationError, EmailDeliveryError, GmailEmailService, RejectedEmailError, RetryableEmailError,
)

BATCH_SIZE = 100


def utc_now() -> datetime:
    return datetime.now(UTC)


class DailyCreditJob:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], now: Callable[[], datetime] = utc_now) -> None:
        self._sessions = sessions
        self._now = now

    async def run(self) -> dict[str, int]:
        day = study_date(self._now())
        processed = granted = 0
        while study_date(self._now()) == day:
            async with self._sessions.begin() as session:
                credits = CreditRepository(session)
                accounts = await credits.lock_due_accounts(day, BATCH_SIZE)
                for account in accounts:
                    amount = min(DAILY_CREDITS, CREDIT_LIMIT - account.balance)
                    credits.apply_daily_grant(account, day, amount)
                    processed += 1
                    granted += int(amount > 0)
            if len(accounts) < BATCH_SIZE:
                break
        return {"processed": processed, "granted": granted}


class StudyReminderJob:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], emails: GmailEmailService,
        frontend_url: str, now: Callable[[], datetime] = utc_now,
    ) -> None:
        self._sessions = sessions
        self._emails = emails
        self._frontend_url = frontend_url.rstrip("/")
        self._now = now

    async def run(self) -> dict[str, int]:
        day = study_date(self._now())
        counts: Counter[str] = Counter()
        async with self._sessions.begin() as session:
            await StudyReminderRepository(session).settle_old_jobs(day, self._now())
        for _ in range(BATCH_SIZE):
            now = self._now()
            if study_date(now) != day:
                break
            async with self._sessions.begin() as session:
                user_id = await StudyReminderRepository(session).claim_one(now)
            if user_id is None:
                break
            counts[await self._deliver(user_id, day)] += 1
        return dict(counts)

    async def _deliver(self, user_id: int, day: date) -> str:
        local = self._now().astimezone(STUDY_TZ)
        async with self._sessions.begin() as session:
            repo = StudyReminderRepository(session)
            if local.date() != day:
                await repo.finish(user_id, day, "expired")
                return "expired"
            email = await repo.recipient(user_id, day, local.time())
            if email is None:
                # This may be a schedule edit or temporary opt-out. Re-evaluate later that day.
                await repo.finish(user_id, day, "pending", next_attempt_at=self._now() + timedelta(minutes=1))
                return "deferred"
            attempt = await repo.begin_attempt(user_id, day)
        if attempt is None:
            return "skipped"

        next_attempt = sent_at = message_id = None
        try:
            message_id = await self._emails.send(
                to=email,
                subject="[Examind] Đến giờ ôn luyện",
                text=f"Đến giờ ôn luyện theo lịch bạn đã chọn.\n\nMở Examind: {self._frontend_url}/dashboard"
                     f"\n\nĐổi lịch hoặc tắt nhắc: {self._frontend_url}/profile#settings",
            )
            status, sent_at = "sent", self._now()
        except RetryableEmailError:
            later = self._now() + timedelta(minutes=attempt * 2)
            if attempt < MAX_ATTEMPTS and study_date(later) == day:
                status, next_attempt = "pending", later
            else:
                status = "failed"
        except (RejectedEmailError, EmailConfigurationError):
            status = "failed"
        except EmailDeliveryError:
            status = "uncertain"
        async with self._sessions.begin() as session:
            await StudyReminderRepository(session).finish(
                user_id, day, status, next_attempt_at=next_attempt, sent_at=sent_at, message_id=message_id,
            )
        return "retry" if status == "pending" else status
