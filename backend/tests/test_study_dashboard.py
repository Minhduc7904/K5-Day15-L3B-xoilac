from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.service.exam_chat_sources import StudentHistory
from app.usecase import study_stats
from app.usecase.study_dashboard import AttemptHistory, StudyDashboard
from app.usecase.study_stats import GradedAttempt
from tests.exam_chat_support import chat_client, login_as, seed
from tests.test_exam_attempts import ROOT, add_draft, seed_attempt_bank

CATALOG = {
    "12C1": {"name": "Ứng dụng đạo hàm", "parent_code": None, "grade": 12},
    "12C11": {"name": "Tính đơn điệu", "parent_code": "12C1", "grade": 12},
    "11C6": {"name": "Mũ và lôgarit", "parent_code": None, "grade": 11},
}
TODAY = date(2026, 11, 28)


async def seed_dashboard_bank(conn):
    await seed(conn)
    await seed_attempt_bank(conn)


def graded(attempt_id, finished, *, draft_id=1, score=5.0, statuses=None, items=None, time_ms=None, minutes=0):
    items = items if items is not None else [{"code": "Q1", "chapter": "12C11", "chapter_codes": ["12C1"]},
                                             {"code": "Q2", "chapter": "11C6", "chapter_codes": ["11C6"]}]
    return GradedAttempt(
        attempt_id=attempt_id, draft_id=draft_id, title=f"Đề {draft_id}", started_at=finished - timedelta(minutes=10),
        finished_at=finished, duration_minutes=minutes, score=score, reason="manual", items=items,
        statuses=statuses or {"Q1": "correct", "Q2": "wrong"}, answers={"Q1": {"value": "A"}, "Q2": {"value": None}},
        time_ms=time_ms or {},
    )


def test_empty_account_has_no_streak_and_no_average():
    data = study_stats.dashboard([], CATALOG, TODAY)
    assert data["totals"] == {"exams": 0, "questions": 0, "minutes": 0, "average": None}
    assert (data["streak"]["current"], data["streak"]["best"]) == (0, 0)
    assert len(data["streak"]["days"]) == 84 and not any(day["studied"] for day in data["streak"]["days"])
    assert data["scores"] == data["chapters"] == data["recent"] == []


def test_study_day_uses_vietnam_midnight():
    # 17:30 UTC ngày 27 = 00:30 ngày 28 giờ Việt Nam.
    late = datetime(2026, 11, 27, 17, 30, tzinfo=UTC)
    assert study_stats.streak([graded(1, late)], TODAY)["days"][-1]["studied"] is True
    before = datetime(2026, 11, 27, 16, 30, tzinfo=UTC)  # 23:30 ngày 27
    days = study_stats.streak([graded(1, before)], TODAY)["days"]
    assert (days[-1]["studied"], days[-2]["studied"]) == (False, True)


def test_streak_counts_from_yesterday_when_today_is_empty_and_tracks_best():
    def at(offset):
        return datetime(2026, 11, 28, 5, tzinfo=UTC) - timedelta(days=offset)  # 12:00 giờ Việt Nam

    attempts = [graded(i, at(offset)) for i, offset in enumerate([1, 2, 3, 10, 11, 12, 13, 14], 1)]
    result = study_stats.streak(attempts, TODAY)
    assert (result["current"], result["best"]) == (3, 5)
    assert study_stats.streak(attempts + [graded(99, at(0))], TODAY)["current"] == 4
    assert study_stats.streak([graded(1, at(2))], TODAY)["current"] == 0


def test_chapters_roll_up_to_parent_and_partial_is_not_correct():
    now = datetime(2026, 11, 28, 5, tzinfo=UTC)
    first = graded(1, now, statuses={"Q1": "partial", "Q2": "correct"})
    second = graded(2, now + timedelta(minutes=1), statuses={"Q1": "correct", "Q2": "skipped"})
    chapters = {c["code"]: c for c in study_stats.dashboard([first, second], CATALOG, TODAY)["chapters"]}
    assert (chapters["12C1"]["correct"], chapters["12C1"]["total"], chapters["12C1"]["grade"]) == (1, 2, 12)
    assert (chapters["11C6"]["correct"], chapters["11C6"]["total"]) == (1, 2)
    assert chapters["12C1"]["name"] == "Ứng dụng đạo hàm"


def test_totals_scores_recent_and_active_minutes():
    now = datetime(2026, 11, 28, 5, tzinfo=UTC)
    attempts = [graded(i, now + timedelta(hours=i), draft_id=1 + i % 2, score=float(i)) for i in range(1, 8)]
    data = study_stats.dashboard(attempts, CATALOG, TODAY)
    assert data["totals"]["exams"] == 2 and data["totals"]["questions"] == 14
    assert data["totals"]["average"] == pytest.approx(4.0)
    assert [p["attempt_id"] for p in data["scores"]] == list(range(1, 8))
    assert [r["attempt"]["attempt_id"] for r in data["recent"]] == [7, 6, 5, 4, 3]
    timed = graded(1, now, time_ms={"Q1": 90_000, "Q2": 30_000}, minutes=1)
    assert timed.duration_seconds == 60  # không vượt thời lượng đề
    assert graded(1, now, time_ms={"Q1": 90_000}).duration_seconds == 90
    assert graded(1, now).duration_seconds == 600  # thiếu thời gian câu thì lấy khoảng nộp trừ bắt đầu


@pytest.mark.asyncio
async def test_dashboard_endpoint_reflects_graded_attempts_and_isolates_users():
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank) as client:
        owner = await login_as(client, "dashboard-owner@example.com")
        assert (await client.get(f"{ROOT}/dashboard")).json()["totals"]["average"] is None

        draft_id = await add_draft(client, owner)
        attempt = (await client.post(f"{ROOT}/exams/{draft_id}/attempts", json={})).json()
        url = f"{ROOT}/attempts/{attempt['attempt_id']}"
        pending = (await client.get(f"{ROOT}/dashboard")).json()
        assert pending["scores"] == [] and pending["streak"]["current"] == 0  # chưa nộp thì chưa tính

        await client.patch(url, json={"question": "Q00801", "answer": "A", "base_revision": 0,
                                      "mutation_id": str(uuid4())})
        assert (await client.post(url + "/submit")).status_code == 200
        data = (await client.get(f"{ROOT}/dashboard")).json()
        assert data["totals"]["exams"] == 1 and data["totals"]["questions"] == 3
        assert data["scores"][0]["attempt_id"] == attempt["attempt_id"]
        assert data["streak"]["current"] == 1 and data["streak"]["days"][-1]["studied"] is True
        assert data["recent"][0]["exam"]["draft_id"] == draft_id
        assert data["chapters"][0]["code"] == "12C1" and data["chapters"][0]["total"] == 3

        await login_as(client, "dashboard-other@example.com")
        other = (await client.get(f"{ROOT}/dashboard")).json()
        assert other["scores"] == [] and other["totals"]["exams"] == 0


@pytest.mark.asyncio
async def test_attempt_history_feeds_the_agent_from_graded_attempts():
    async with chat_client(real_auth=True, seed_fn=seed_dashboard_bank) as client:
        owner = await login_as(client, "history-owner@example.com")
        draft_id = await add_draft(client, owner)
        attempt = (await client.post(f"{ROOT}/exams/{draft_id}/attempts", json={})).json()
        await client.post(f"{ROOT}/attempts/{attempt['attempt_id']}/submit")
        async with client.db() as session:
            from app.repositories.exam_attempts import ExamAttemptRepository
            from app.repositories.question_bank_repository import QuestionBankRepository

            history = AttemptHistory(StudyDashboard(ExamAttemptRepository(session), QuestionBankRepository(session)))
            found = await history.get(f"U{owner}")
            assert isinstance(found, StudentHistory)
            chapter = next(c for c in found.chapters if c.code == "12C1")
            assert (chapter.correct, chapter.total, chapter.skipped, chapter.error_rate) == (0, 0, 3, None)
            assert found.attempt_count == 1
            assert await history.get("U999999") is None
            assert await history.get("not-a-ref") is None
