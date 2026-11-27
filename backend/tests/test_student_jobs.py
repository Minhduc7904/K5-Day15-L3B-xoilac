from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select, update

from app.models.student import CreditAccount, CreditLedger, StudyReminderDelivery
from app.models.user import User
from app.service.email_service import EmailDeliveryError, RetryableEmailError
from app.usecase.student_jobs import DailyCreditJob, StudyReminderJob
from tests.conftest import FakeEmail
from tests.test_auth import register
from tests.test_student_profile import DETAILS, PROFILE


async def test_daily_credit_job_uses_vietnam_midnight_and_caps_the_balance(db, client):
    user_ids = [(await register(client, f"student{i}@example.com")).json()["user_id"] for i in range(3)]
    day = date(2026, 11, 30)
    async with db.begin() as session:
        for user_id, amount in zip(user_ids, (350, 450, 500)):
            account = await session.get(CreditAccount, user_id)
            account.balance = amount
            account.last_daily_processed_on = day

    before_midnight = datetime(2026, 11, 30, 16, 59, tzinfo=UTC)
    assert await DailyCreditJob(db, lambda: before_midnight).run() == {"processed": 0, "granted": 0}
    after_midnight = before_midnight + timedelta(minutes=1)
    assert await DailyCreditJob(db, lambda: after_midnight).run() == {"processed": 3, "granted": 2}
    assert await DailyCreditJob(db, lambda: after_midnight).run() == {"processed": 0, "granted": 0}
    async with db() as session:
        balances = await session.scalars(select(CreditAccount.balance).order_by(CreditAccount.user_id))
        assert list(balances) == [450, 500, 500]
        grants = await session.scalars(select(CreditLedger.delta).where(
            CreditLedger.reason == "daily_grant", CreditLedger.effective_on == day + timedelta(days=1),
        ).order_by(CreditLedger.id))
        assert list(grants) == [100, 50]


async def test_reminder_checks_local_day_and_time_and_does_not_resend(db, client):
    user_id = (await register(client)).json()["user_id"]
    assert (await client.put(PROFILE, json=DETAILS)).status_code == 200
    emails = FakeEmail()
    monday_before_due = datetime(2026, 11, 30, 0, 59, tzinfo=UTC)
    assert not await StudyReminderJob(db, emails, "https://example.com", lambda: monday_before_due).run()
    due = monday_before_due + timedelta(minutes=1)
    assert await StudyReminderJob(db, emails, "https://example.com", lambda: due).run() == {"sent": 1}
    assert not await StudyReminderJob(db, emails, "https://example.com", lambda: due).run()

    # Tuesday was not selected. Saturday was selected, but the student turns reminders off.
    assert not await StudyReminderJob(db, emails, "https://example.com", lambda: due + timedelta(days=1)).run()
    assert (await client.put(PROFILE, json={**DETAILS, "reminder_time": None})).status_code == 200
    assert not await StudyReminderJob(db, emails, "https://example.com", lambda: due + timedelta(days=5)).run()

    # A legacy email cannot be used for reminders and does not cancel profile completion.
    async with db.begin() as session:
        await session.execute(update(User).where(User.user_id == user_id).values(email_verified_at=None))
    assert (await client.put(PROFILE, json=DETAILS)).json()["code"] == "REMINDER_EMAIL_UNVERIFIED"
    assert len(emails.outbox) == 1


async def test_worker_retries_known_rejection_but_never_ambiguous_send(db, client):
    user_id = (await register(client)).json()["user_id"]
    await client.put(PROFILE, json=DETAILS)

    class FailingEmail:
        attempts = 0

        async def send(self, **message):
            self.attempts += 1
            if self.attempts == 1:
                raise RetryableEmailError()
            raise EmailDeliveryError()

    mail = FailingEmail()
    due = datetime(2026, 11, 30, 1, tzinfo=UTC)
    assert await StudyReminderJob(db, mail, "", lambda: due).run() == {"retry": 1}
    assert not await StudyReminderJob(db, mail, "", lambda: due + timedelta(minutes=1)).run()
    later = due + timedelta(minutes=2)
    assert await StudyReminderJob(db, mail, "", lambda: later).run() == {"uncertain": 1}
    assert not await StudyReminderJob(db, mail, "", lambda: later + timedelta(minutes=5)).run()
    async with db() as session:
        delivery = await session.get(StudyReminderDelivery, (user_id, date(2026, 11, 30)))
        assert delivery.status == "uncertain" and delivery.attempt_count == 2
