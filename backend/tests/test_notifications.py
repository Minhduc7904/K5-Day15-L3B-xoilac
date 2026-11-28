import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.api.realtime import NOTIFICATION_NEW, RealtimeServer
from app.models.exam_attempt import ExamAttempt
from app.models.notification import Notification
from app.models.session import UserSession
from app.models.student import CreditAccount
from app.repositories.exam_chat_repository import ExamChatRepository
from app.repositories.notifications import NotificationRepository
from app.usecase.student_jobs import DailyCreditJob, StudyReminderJob
from app.worker import expire_exams
from tests.conftest import FakeEmail
from tests.exam_chat_support import chat_client, login_as
from tests.test_auth import register
from tests.test_exam_attempts import ROOT, add_draft, seed_attempt_bank
from tests.test_student_profile import DETAILS, PROFILE

URL = "/api/v1/student/me/notifications"


async def kinds(db, user_id):
    async with db() as session:
        return list(await session.scalars(
            select(Notification.kind).where(Notification.user_id == user_id).order_by(Notification.id)
        ))


@pytest.mark.asyncio
async def test_list_read_and_ownership():
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank) as client:
        owner = await login_as(client, "notice-owner@example.com")
        async with client.db() as session:
            repo = NotificationRepository(session)
            for number in range(3):
                await repo.add(owner, "draft_ready", f"Đề {number}", dedupe_key=f"draft:{number}", link="/exams")
            await repo.add(owner, "draft_ready", "Trùng", dedupe_key="draft:0")  # cùng khóa thì bỏ qua
            await session.commit()
        page = (await client.get(URL, params={"limit": 2})).json()
        assert [n["title"] for n in page["items"]] == ["Đề 2", "Đề 1"]
        assert page["unread"] == 3 and page["next_before_id"] == page["items"][-1]["id"]
        rest = (await client.get(URL, params={"limit": 2, "before_id": page["next_before_id"]})).json()
        assert [n["title"] for n in rest["items"]] == ["Đề 0"] and rest["next_before_id"] is None

        first = page["items"][0]["id"]
        assert (await client.post(f"{URL}/{first}/read")).status_code == 204
        assert (await client.post(f"{URL}/{first}/read")).status_code == 204  # đọc lại không lỗi
        assert (await client.get(URL)).json()["unread"] == 2
        assert (await client.post(f"{URL}/read-all")).status_code == 204
        assert (await client.get(URL)).json()["unread"] == 0

        await login_as(client, "notice-other@example.com")
        assert (await client.get(URL)).json() == {"items": [], "unread": 0, "next_before_id": None}
        assert (await client.post(f"{URL}/{first}/read")).status_code == 404
        assert (await client.post(f"{URL}/999999/read")).status_code == 404


@pytest.mark.asyncio
async def test_timeout_notifies_once_with_result_link():
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank) as client:
        owner = await login_as(client, "notice-timeout@example.com")
        draft = await add_draft(client, owner, minutes=1)
        attempt_id = (await client.post(f"{ROOT}/exams/{draft}/attempts", json={})).json()["attempt_id"]
        assert (await client.get(URL)).json()["items"] == []
        async with client.db() as session:
            await session.execute(update(ExamAttempt).where(ExamAttempt.attempt_id == attempt_id)
                                  .values(deadline_at=datetime.now(UTC) - timedelta(seconds=1)))
            await session.commit()
        assert await expire_exams(client.db) == {"graded": 1}
        assert await expire_exams(client.db) == {"graded": 0}
        assert (await client.get(f"{ROOT}/attempts/{attempt_id}")).status_code == 200  # đọc lại không báo thêm
        items = (await client.get(URL)).json()["items"]
        assert [(n["kind"], n["link"]) for n in items] == [("attempt_graded", f"/results/online-{attempt_id}")]
        assert "0/10" in items[0]["body"]

        manual = await add_draft(client, owner)
        started = (await client.post(f"{ROOT}/exams/{manual}/attempts", json={})).json()["attempt_id"]
        await client.post(f"{ROOT}/attempts/{started}/submit")
        assert len((await client.get(URL)).json()["items"]) == 1  # nộp tay không sinh thông báo


@pytest.mark.asyncio
async def test_draft_ready_notification_is_not_repeated_for_the_same_draft():
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank) as client:
        owner = await login_as(client, "notice-draft@example.com")
        draft_id = await add_draft(client, owner)
        async with client.db() as session:
            repo = ExamChatRepository(session)
            from app.models.exam_chat import ExamDraft

            draft = await session.get(ExamDraft, draft_id)
            await repo.notify_draft_ready(draft.session_id, draft)
            await repo.notify_draft_ready(draft.session_id, draft)
        items = (await client.get(URL)).json()["items"]
        assert [(n["kind"], n["link"]) for n in items] == [("draft_ready", f"/exams/draft-{draft_id}")]


async def test_daily_credit_notifies_only_granted_accounts_once(db, client):
    ids = [(await register(client, f"credit{i}@example.com")).json()["user_id"] for i in range(2)]
    day = date(2026, 11, 30)
    async with db.begin() as session:
        for user_id, amount in zip(ids, (350, 500)):
            account = await session.get(CreditAccount, user_id)
            account.balance, account.last_daily_processed_on = amount, day
    tomorrow = datetime(2026, 11, 30, 17, 1, tzinfo=UTC)
    await DailyCreditJob(db, lambda: tomorrow).run()
    await DailyCreditJob(db, lambda: tomorrow).run()
    assert await kinds(db, ids[0]) == ["credit_granted"]
    assert await kinds(db, ids[1]) == []  # đã đầy 500, không cộng nên không báo
    async with db() as session:
        notice = await session.scalar(select(Notification).where(Notification.user_id == ids[0]))
        assert notice.title == "Đã cộng 100 credit hằng ngày" and notice.link == "/profile#credit"


async def test_reminder_sent_notifies_once_per_day(db, client):
    user_id = (await register(client)).json()["user_id"]
    assert (await client.put(PROFILE, json=DETAILS)).status_code == 200
    due = datetime(2026, 11, 30, 1, 0, tzinfo=UTC)
    job = StudyReminderJob(db, FakeEmail(), "https://example.com", lambda: due)
    assert await job.run() == {"sent": 1}
    assert not await job.run()
    assert await kinds(db, user_id) == ["study_reminder"]


@pytest.mark.asyncio
async def test_watcher_pushes_new_notifications_only_to_the_connected_owner(monkeypatch):
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank) as client:
        owner = await login_as(client, "notice-live@example.com")
        stranger = await login_as(client, "notice-live-other@example.com")
        async with client.db() as session:
            sessions = {row.user_id: row.session_id for row in await session.scalars(select(UserSession))}
        pushed = []
        realtime = RealtimeServer([], lambda: client.db)

        async def collect(event, payload=None, *, to=None):
            pushed.append((event, payload, to))

        async def room(*args):
            pass

        monkeypatch.setattr(realtime.server, "enter_room", room)
        monkeypatch.setattr(realtime.server, "emit", collect)
        assert await realtime.connect("owner", {}, {"ticket": realtime.tickets.issue(sessions[owner])})
        try:
            await asyncio.sleep(0.2)  # watcher đã ghi nhận mốc id ban đầu
            async with client.db() as session:
                repo = NotificationRepository(session)
                await repo.add(owner, "draft_ready", "Cho chủ", dedupe_key="mine", link="/exams")
                await repo.add(stranger, "draft_ready", "Cho người khác", dedupe_key="theirs")
                await session.commit()
            for _ in range(40):
                if pushed:
                    break
                await asyncio.sleep(0.1)
            assert [(event, payload["title"], to) for event, payload, to in pushed] == [
                (NOTIFICATION_NEW, "Cho chủ", f"user:{owner}")
            ]
        finally:
            await realtime.disconnect("owner")
            if realtime._notice_watch:
                await asyncio.wait_for(realtime._notice_watch, 5)
