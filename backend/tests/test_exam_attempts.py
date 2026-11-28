import asyncio
import os
from datetime import UTC, datetime, timedelta
from fractions import Fraction
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.realtime import RealtimeServer
from app.models.exam_attempt import ExamAttempt
from app.models.exam_chat import ExamChatSession, ExamDraft
from app.models.session import UserSession
from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.question_bank_repository import QuestionBankRepository, statements
from app.schemas.exam_attempt import AttemptSave
from app.usecase.exam_scoring import allocate_points, grade_question
from app.worker import expire_exams
from tests.exam_chat_support import chat_client, login_as, no_answers

ROOT = "/api/v1/study"
ROWS = ((801, "SINGLE_CHOICE"), (802, "TRUE_FALSE"), (803, "SHORT_ANSWER"))


async def seed_attempt_bank(conn):
    for qid, kind in ROWS:
        await conn.execute(text(
            "INSERT INTO questions (question_id, content, type, difficulty, visibility, correct_answer, solution"
            + (", slug" if conn.dialect.name == "postgresql" else "")
            + ") VALUES (:qid, :content, :kind, 'NB', 'PUBLISHED', :answer, 'Lời giải mẫu'"
            + (", :slug" if conn.dialect.name == "postgresql" else "") + ")"
            + (" ON CONFLICT DO NOTHING" if conn.dialect.name == "postgresql" else "")
        ), {"qid": qid, "kind": kind, "content": f"Câu mẫu {qid}", "answer": "1,20" if qid == 803 else None,
            "slug": f"attempt-test-{qid}"})
    statement_insert = (pg_insert(statements).on_conflict_do_nothing() if conn.dialect.name == "postgresql"
                        else insert(statements))
    await conn.execute(statement_insert, [
        {"statement_id": qid * 10 + i, "question_id": qid, "order": i, "content": f"Phương án {i}",
         "is_correct": flag}
        for qid, flags in [(801, (True, False)), (802, (False, True, False, True))]
        for i, flag in enumerate(flags, 1)
    ])


async def add_draft(client, user_id, minutes=None, *, chapter="12C1"):
    async with client.db() as session:
        chat = ExamChatSession(student_ref=f"U{user_id}", user_id=user_id)
        session.add(chat)
        await session.flush()
        bank = QuestionBankRepository(session)
        items = await bank.load_items([qid for qid, _ in ROWS])
        draft = ExamDraft(
            session_id=chat.session_id, title="Đề luyện tập mẫu", preview_version=1,
            structure={"kind": "CHAPTER", "chapters": [{"code": chapter, "count": 3}],
                       "duration_minutes": minutes},
            items=[{"order": i, "chapter": chapter, **item} for i, item in enumerate(items.values(), 1)],
            shortages=[],
        )
        session.add(draft)
        await session.commit()
        return draft.draft_id


def test_allocates_exact_group_points_and_uses_template_when_present():
    items = [{"type": kind} for kind, count in [("SINGLE_CHOICE", 7), ("TRUE_FALSE", 3), ("SHORT_ANSWER", 4)]
             for _ in range(count)]
    allocated = allocate_points(items, {})
    for kind, target in [("SINGLE_CHOICE", 3), ("TRUE_FALSE", 4), ("SHORT_ANSWER", 3)]:
        group = [Fraction(item["points_exact"]) for item in allocated if item["type"] == kind]
        assert sum(group) == target
        assert len(set(group)) == 1
    fixed = [{"type": "SINGLE_CHOICE", "section_order": 1}, {"type": "TRUE_FALSE", "section_order": 2}]
    structure = {"sections": [{"order": 1, "points_per_question": 3}, {"order": 2, "points_per_question": 7}]}
    assert [item["points"] for item in allocate_points(fixed, structure)] == [3, 7]
    structure["sections"][1]["points_per_question"] = 2
    scaled = allocate_points(fixed, structure)
    assert [item["points"] for item in scaled] == [3, 2]
    assert [item["max_points"] for item in scaled] == [6, 4]
    structure["sections"][1]["points_per_question"] = None
    assert [item["points"] for item in allocate_points(fixed, structure)] == [3, 7]
    adjusted = allocate_points(fixed, {"type_point_weights": {"SINGLE_CHOICE": 20, "TRUE_FALSE": 60, "SHORT_ANSWER": 20}})
    assert [item["points"] for item in adjusted] == [2.5, 7.5]


@pytest.mark.parametrize("count,factor", list(enumerate(("0", "0.10", "0.25", "0.50", "1"))))
def test_true_false_awards_fraction_of_max_and_never_credits_blank(count, factor):
    expected = [False, True, False, True]
    points, _, matches = grade_question({"type": "TRUE_FALSE", "points_exact": "4/5"},
                                        {"statements": expected}, expected[:count] + [None] * (4 - count))
    assert matches == count
    assert points == Fraction(4, 5) * Fraction(factor)


@pytest.mark.asyncio
async def test_resume_rejects_stale_update_and_grades_fixed_snapshot():
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank) as client:
        owner = await login_as(client, "attempt-owner@example.com")
        draft_id = await add_draft(client, owner)
        start_url = f"{ROOT}/exams/{draft_id}/attempts"
        started = await client.post(start_url, json={})
        assert started.status_code == 200, started.text
        attempt = started.json()
        no_answers(attempt["draft"])
        assert attempt["deadline_at"] is None

        url = f"{ROOT}/attempts/{attempt['attempt_id']}"
        assert (await client.post(start_url, json={"restart": True})).json()["attempt_id"] == attempt["attempt_id"]
        mutation = {"question": "Q00801", "base_revision": 0, "answer": "A", "mutation_id": str(uuid4())}
        save = await client.patch(url, json=mutation)
        assert save.status_code == 200, save.text
        assert (await client.patch(url, json=mutation)).json()["revision"] == save.json()["revision"]
        stale = await client.patch(url, json={**mutation, "mutation_id": str(uuid4()), "answer": "B"})
        assert stale.json()["detail"]["code"] == "ANSWER_CONFLICT"
        assert (await client.get(url)).json()["answers"]["Q00801"]["value"] == "A"
        assert (await client.get(f"{ROOT}/attempts")).json()[str(draft_id)]["active"] is True
        assert (await client.get(url + "/result")).status_code == 409

        for code, value in [("Q00802", [False, True, False, None]), ("Q00803", "1.2")]:
            response = await client.patch(url, json={"question": code, "answer": value,
                                                     "base_revision": 0, "mutation_id": str(uuid4())})
            assert response.status_code == 200, response.text
        async with client.db() as session:
            await session.execute(text("UPDATE questions SET correct_answer = '99' WHERE question_id = 803"))
            await session.commit()
        assert (await client.post(url + "/submit")).json()["reason"] == "manual"
        result = (await client.get(url + "/result")).json()
        assert result["grading"]["score"] == 8
        assert result["attempt"]["correct"] == 2
        summary = (await client.get(f"{ROOT}/attempts")).json()[str(draft_id)]
        assert (summary["best_score"], summary["count"], summary["active"]) == (8, 1, False)
        assert (await client.post(url + "/submit")).json()["score"] == 8
        new_attempt = (await client.post(start_url, json={"restart": True})).json()
        assert new_attempt["attempt_id"] != attempt["attempt_id"]
        assert new_attempt["answers"] == {}

        await login_as(client, "another-student@example.com")
        for path in [url, url + "/result", start_url]:
            assert (await client.get(path)).status_code == 404


@pytest.mark.asyncio
async def test_worker_expires_attempt_without_connected_client_and_socket_requires_owner(monkeypatch):
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank) as client:
        owner = await login_as(client, "timed-owner@example.com")
        draft = await add_draft(client, owner, minutes=1)
        started = (await client.post(f"{ROOT}/exams/{draft}/attempts", json={})).json()
        attempt_id = started["attempt_id"]
        url = f"{ROOT}/attempts/{attempt_id}"
        tab = str(uuid4())
        async with client.db() as session:
            delta = datetime.now(UTC) - timedelta(seconds=15)
            await session.execute(update(ExamAttempt).where(ExamAttempt.attempt_id == attempt_id)
                                  .values(started_at=delta))
            await session.commit()
        first = {"question": "Q00801", "base_revision": 0, "answer": "A", "mutation_id": str(uuid4()),
                 "tab_id": tab, "elapsed_ms": 5000}
        saved = (await client.patch(url, json=first)).json()
        assert saved["question_seconds"] == {"Q00801": 5}
        competing_tab = {"question": "Q00801", "mutation_id": str(uuid4()), "tab_id": str(uuid4()), "elapsed_ms": 5000}
        assert (await client.patch(url, json=competing_tab)).json()["question_seconds"] == {"Q00801": 5}

        intruder = await login_as(client, "timed-intruder@example.com")
        async with client.db() as session:
            sessions = {row.user_id: row.session_id for row in await session.scalars(
                select(UserSession)
            )}
        notifications = []
        realtime = RealtimeServer([], lambda: client.db)
        async def collect(event, payload, *, to):
            notifications.append((event, payload, to))
        async def room(*args):
            pass
        monkeypatch.setattr(realtime.server, "enter_room", room)
        monkeypatch.setattr(realtime.server, "leave_room", room)
        monkeypatch.setattr(realtime.server, "emit", collect)
        owner_ticket = realtime.tickets.issue(sessions[owner])
        stranger_ticket = realtime.tickets.issue(sessions[intruder])
        assert await realtime.connect("owner", {}, {"ticket": owner_ticket})
        assert await realtime.connect("stranger", {}, {"ticket": stranger_ticket})
        try:
            denial = await realtime.join_attempt("stranger", {"attempt_id": attempt_id})
            assert denial["code"] == "ATTEMPT_NOT_FOUND"
            joined = await realtime.join_attempt("owner", {"attempt_id": attempt_id})
            assert joined["ok"]
            async with client.db() as session:
                await session.execute(update(ExamAttempt).where(ExamAttempt.attempt_id == attempt_id)
                                      .values(deadline_at=datetime.now(UTC) - timedelta(seconds=1)))
                await session.commit()

            assert await expire_exams(client.db) == {"graded": 1}
            assert await expire_exams(client.db) == {"graded": 0}
            for _ in range(20):
                if notifications:
                    break
                await asyncio.sleep(0.1)
            assert notifications[0][0] == "attempt:finished"
            assert notifications[0][1]["reason"] == "timeout"
            assert notifications[0][2] == f"attempt:{attempt_id}"
            late = await realtime.save_attempt("owner", {"attempt_id": attempt_id, "update": {
                "question": "Q00803", "base_revision": 0, "answer": "1,2", "mutation_id": str(uuid4()),
            }})
            assert late["code"] == "ATTEMPT_FINISHED"
            async with client.db() as session:
                row = await ExamAttemptRepository(session).get(attempt_id)
                assert (row.result["score"], row.status) == (3, "graded")
        finally:
            await realtime.disconnect("owner")
            await realtime.disconnect("stranger")
            if realtime._attempt_watch:
                await realtime._attempt_watch


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("EXAM_ATTEMPT_TEST_DATABASE_URL"), reason="requires a clean migrated PostgreSQL database")
async def test_postgresql_serializes_competing_start_and_submit():
    async with chat_client(real_auth=True, seed_fn=seed_attempt_bank,
                           database_url=os.environ["EXAM_ATTEMPT_TEST_DATABASE_URL"]) as client:
        owner = await login_as(client, f"concurrent-{uuid4().hex}@example.com")
        draft_id = await add_draft(client, owner, minutes=2)
        path = f"{ROOT}/exams/{draft_id}/attempts"
        starts = await asyncio.gather(*(client.post(path, json={}) for _ in range(4)))
        assert all(response.status_code == 200 for response in starts)
        ids = {response.json()["attempt_id"] for response in starts}
        assert len(ids) == 1
        url = f"{ROOT}/attempts/{ids.pop()}/submit"
        finishes = await asyncio.gather(*(client.post(url) for _ in range(4)))
        assert all(response.status_code == 200 for response in finishes)
        assert {response.json()["revision"] for response in finishes} == {1}
        assert {response.json()["finished_at"] for response in finishes} == {finishes[0].json()["finished_at"]}
        assert (await client.get(f"{ROOT}/attempts")).json()[str(draft_id)]["count"] == 1
