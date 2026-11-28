from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from app.models.exam_attempt import ExamAttempt
from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.usecase.study_dashboard import AttemptHistory, StudyDashboard
from app.usecase.study_stats import attempt_review
from tests.exam_chat_support import chat_client, login_as
from tests.test_exam_attempts import ROOT, add_draft
from tests.test_study_dashboard import CATALOG, graded, seed_dashboard_bank


def test_review_counts_answered_only_and_keeps_latest_and_earlier():
    now = datetime.now(UTC)
    items = [{"code": f"Q{i}", "chapter_codes": ["12C1"], "subchapter_codes": ["12C11"]}
             for i in range(6)]
    last = graded(2, now, items=items, statuses=dict(zip(
        (i["code"] for i in items), ("wrong", "partial", "correct", "wrong", "correct", "skipped"),
    )))
    older = graded(1, now - timedelta(days=1), items=items[:1], statuses={"Q0": "correct"})
    result = attempt_review([last, older], CATALOG, 12, ["12C11"])
    [chapter] = result.chapters
    assert (chapter.total, chapter.correct, chapter.incorrect, chapter.skipped) == (6, 3, 3, 1)
    assert chapter.error_rate == 0.50 and chapter.classification == "weak"
    assert result.latest[0].incorrect == 3 and result.latest[0].total == 5
    assert result.earlier[0].correct == result.earlier[0].total == 1
    assert not result.conflicting  # The same question can change outcomes between attempts.


def test_review_discloses_missing_and_conflicting_evidence():
    now = datetime.now(UTC)
    catalog = {**CATALOG, "12C4": {"name": "Tích phân", "parent_code": None, "grade": 12}}
    items = [{"code": code, "chapter": "12C1"} for code in ("Q1", "Q2", "Q3")]
    attempt = graded(1, now, items=items, statuses={"Q1": "wrong", "Q3": "correct"})
    attempt.conflicts.add("Q3")
    result = attempt_review([attempt], catalog, 12, [])
    assert result.conflicting and result.conflicting_items == 1 and result.incomplete == 1
    small, unseen = result.chapters
    assert small.classification == "under_practiced" and small.error_rate == 1
    assert unseen.classification == "unpracticed" and unseen.error_rate is None


@pytest.mark.asyncio
async def test_shared_reader_limits_history_and_isolates_students():
    async with chat_client(real_auth=True, seed_fn=seed_dashboard_bank) as client:
        student = await login_as(client, "recent-owner@example.com")
        now = datetime.now(UTC)
        for i in range(7):
            draft_id = await add_draft(client, student)
            started = (await client.post(f"{ROOT}/exams/{draft_id}/attempts", json={})).json()
            url = f"{ROOT}/attempts/{started['attempt_id']}"
            answer = "A" if i == 0 else "B"
            assert (await client.patch(url, json={"question": "Q00801", "answer": answer,
                                                  "base_revision": 0, "mutation_id": str(uuid4())})).status_code == 200
            assert (await client.post(url + "/submit")).status_code == 200
            # ID 1 was graded last and ID 7 is outside the window.
            graded_at = now - timedelta(days=31 if i == 6 else i)
            async with client.db() as session:
                await session.execute(update(ExamAttempt).where(ExamAttempt.attempt_id == started["attempt_id"])
                                      .values(graded_at=graded_at, finished_at=graded_at))
                await session.commit()
        other = await login_as(client, "recent-other@example.com")
        async with client.db() as session:
            reader = AttemptHistory(StudyDashboard(ExamAttemptRepository(session), QuestionBankRepository(session)))
            assert await reader.get(f"U{other}", grade=12) is None
            result = await reader.get(f"U{student}", grade=12)
            assert result.attempt_count == 5
            chapter = next(c for c in result.chapters if c.code == "12C1")
            assert (chapter.total, chapter.correct, chapter.incorrect, chapter.skipped) == (5, 1, 4, 10)
            latest = next(c for c in result.latest if c.code == "12C1")
            assert latest.correct == latest.total == 1
            await session.execute(update(ExamAttempt).where(ExamAttempt.user_id == student)
                                  .values(graded_at=now - timedelta(days=32)))
            await session.commit()
            result = await reader.get(f"U{student}", grade=12)
            assert result.latest_at is not None and result.attempt_count == 0
