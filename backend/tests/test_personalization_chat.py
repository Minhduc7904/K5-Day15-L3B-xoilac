import logging
import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import Cookies
from sqlalchemy import update

from app.api.deps import get_student_history
from app.core.config import get_settings
from app.main import app
from app.models.exam_attempt import ExamAttempt
from app.repositories.question_bank_repository import questions
from app.service.exam_chat_model import ChatAction, ExamChatModel, ExamChatModelError, PracticeRecommendation
from tests.exam_chat_support import BASE, chat_client, login_as, new_session, no_answers, say
from tests.test_exam_attempts import ROOT, add_draft
from tests.test_live_exam_chat import PROFILE, confirm, live
from tests.test_study_dashboard import seed_dashboard_bank

HISTORY_CHAT = "Dựa trên các lượt đã chấm, gợi ý bài em nên làm tiếp."


async def set_grade(client):
    result = await client.put(PROFILE, json={
        "school_name": "THPT Mẫu", "grade": 12, "target_score": 8,
        "exam_period": "final_1", "study_days": [1, 3],
    })
    assert result.status_code == 200


async def grade(client, draft_id, *, correct=False, only_one=False):
    response = await client.post(f"{ROOT}/exams/{draft_id}/attempts", json={"restart": True})
    assert response.status_code == 200
    attempt_id = response.json()["attempt_id"]
    url = f"{ROOT}/attempts/{attempt_id}"
    answers = {
        "Q00801": "A" if correct else "B",
        "Q00802": [False, True, False, True] if correct else [True, False, True, False],
        "Q00803": "1.2" if correct else "2",
    }
    for code, value in answers.items():
        result = await client.patch(url, json={"question": code, "answer": value, "base_revision": 0,
                                               "mutation_id": str(uuid4())})
        assert result.status_code == 200
        if only_one:
            break
    assert (await client.post(url + "/submit")).status_code == 200
    return attempt_id


def plan(chapter, evidence, rationale="reinforce_basics", count=2):
    return PracticeRecommendation.model_validate({"groups": [{
        "chapter_code": chapter, "type": "SINGLE_CHOICE", "difficulty": "TH",
        "count": count, "evidence_ref": evidence, "rationale": rationale,
    }]})


@pytest.fixture
def recommend(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(ExamChatModel, "recommend", lambda _self, context: mock(context))
    return mock


async def test_recommendation_requests_strict_output_schema(monkeypatch):
    model = ExamChatModel(get_settings())
    expected = plan("12C11", "12C1", count=1)
    call = AsyncMock(return_value={"content": expected.model_dump_json()})
    monkeypatch.setattr(model, "_call", call)
    cell = expected.groups[0].model_dump(exclude={"count"})
    recommendation = await model.recommend({"bank": [cell], "total": 1})
    assert recommendation.groups[0].evidence_ref == "12C1"
    response_format = call.call_args.kwargs["response_format"]
    assert response_format["type"] == "json_schema" and response_format["json_schema"]["strict"]
    group = response_format["json_schema"]["schema"]["$defs"]["PracticeGroup"]
    assert set(group["required"]) == {"chapter_code", "difficulty", "type", "count", "evidence_ref", "rationale"}
    assert group["properties"]["chapter_code"]["enum"] == ["12C11"]
    assert group["properties"]["count"]["maximum"] == 1


async def test_history_personalizes_same_request_and_refreshes_after_grading(live, recommend):
    live.return_value = ChatAction(action="history", total=2)
    recommend.side_effect = [
        plan("12C11", "12C1"), plan("12C4", "12C4", "assess_coverage"), plan("12C4", "12C4"),
    ]
    async with chat_client(real_auth=True, seed_fn=seed_dashboard_bank) as client:
        app.dependency_overrides.pop(get_student_history)
        student = await login_as(client, "personal-one@example.com")
        await set_grade(client)
        draft_id = await add_draft(client, student)
        for _ in range(2):
            await grade(client, draft_id)
        sid = await new_session(client, None)
        reply, first, _ = await say(client, sid, HISTORY_CHAT)
        assert "sai 6/6" in reply and first["structure"]["chapters"] == [{"code": "12C11", "count": 2}]
        model_input = recommend.call_args.args[0]
        assert model_input["evidence"]["12C1"]["latest"]["incorrect"] == 3
        assert model_input["evidence"]["12C1"]["earlier"]["attempted"] == 3
        assert model_input["evidence"]["12C4"]["status"] == "unpracticed"
        assert "11C6" not in model_input["evidence"]
        assert "personal-one" not in str(model_input) and "Q00801" not in str(model_input)

        for _ in range(3):
            await grade(client, draft_id, correct=True)
        _, refreshed, _ = await say(client, sid, HISTORY_CHAT)
        assert refreshed["version"] > first["version"]
        assert refreshed["structure"]["chapters"] == [{"code": "12C4", "count": 2}]
        assert recommend.call_args.args[0]["evidence"]["12C1"]["recent"]["error_rate"] == 0.40

        second_student = await login_as(client, "personal-two@example.com")
        await set_grade(client)
        separate = await add_draft(client, second_student, chapter="12C4")
        for _ in range(2):
            await grade(client, separate)
        assert (await client.post(f"{BASE}/sessions/{sid}/messages", json={"text": "Tạo đề ôn tiếp"})).status_code == 404
        second_sid = await new_session(client, None)
        _, second, _ = await say(client, second_sid, HISTORY_CHAT)
        assert second["structure"]["chapters"] == [{"code": "12C4", "count": 2}]
        assert recommend.call_args.args[0]["evidence"]["12C1"]["recent"]["attempted"] == 0


async def test_history_insufficient_conflicting_invalid_and_shortage(live, recommend):
    live.return_value = ChatAction(action="history", total=2)
    recommend.side_effect = [
        plan("12C11", "12C1"), plan("12C11", "12C1", "assess_coverage"), ExamChatModelError("offline"),
    ]
    async with chat_client(real_auth=True, seed_fn=seed_dashboard_bank) as client:
        app.dependency_overrides.pop(get_student_history)
        owner = await login_as(client, "history-edge@example.com")
        await set_grade(client)
        sid = await new_session(client, None)
        reply, preview, _ = await say(client, sid, HISTORY_CHAT)
        assert "chưa có lịch sử" in reply and not preview
        recommend.assert_not_awaited()
        attempt_id = await grade(client, await add_draft(client, owner), only_one=True)
        reply, preview, _ = await say(client, sid, HISTORY_CHAT)
        assert "sai 1/1" in reply and "ít dữ liệu" in reply and not preview
        reply, preview, _ = await say(client, sid, HISTORY_CHAT)
        assert "có thêm dữ liệu" in reply and preview
        reply, preview, _ = await say(client, sid, HISTORY_CHAT)
        assert "AI đang bận" in reply and not preview

        live.return_value = ChatAction(action="history", total=50, chapters=["12C1"])
        reply, preview, _ = await say(client, sid, HISTORY_CHAT)
        assert "Kho có 4/50" in reply and not preview and recommend.await_count == 3

        async with client.db() as session:
            attempt = await session.get(ExamAttempt, attempt_id)
            result = attempt.result
            attempt.result = {**result, "results": [*result["results"], {"code": "Q00801", "status": "correct"}]}
            await session.commit()
        reply, preview, _ = await say(client, sid, HISTORY_CHAT)
        assert "mâu thuẫn" in reply and not preview and recommend.await_count == 3


async def test_history_preview_edits_and_rechecks_bank_at_confirm(live, recommend):
    live.side_effect = [ChatAction(action="history", total=3), ChatAction(action="edit", total=2)]
    recommend.return_value = plan("12C11", "12C1", count=3)
    async with chat_client(real_auth=True, seed_fn=seed_dashboard_bank) as client:
        app.dependency_overrides.pop(get_student_history)
        owner = await login_as(client, "history-build@example.com")
        await set_grade(client)
        draft_id = await add_draft(client, owner)
        for _ in range(2):
            await grade(client, draft_id)
        sid = await new_session(client, None)
        _, first, draft = await say(client, sid, HISTORY_CHAT)
        assert first["structure"]["rows"][0]["count"] == 3 and not draft
        _, edited, _ = await say(client, sid, "Còn hai câu")
        assert edited["structure"]["rows"][0]["count"] == 2
        result = await client.patch(f"{BASE}/sessions/{sid}/preview", json={
            "version": edited["version"], "edit": {"rows": [{**edited["structure"]["rows"][0], "count": 3}]},
        })
        assert result.status_code == 200
        assert (await confirm(client, sid, edited["version"])).status_code == 409
        async with client.db() as session:
            await session.execute(update(questions).where(questions.c.question_id.in_([3, 4]))
                                  .values(visibility="DRAFT"))
            await session.commit()
        offer = (await confirm(client, sid, result.json()["version"])).json()
        assert offer["draft"] is None and offer["preview"]["offer"]["count"] == 2
        built = (await confirm(client, sid, offer["preview"]["version"], count=2)).json()["draft"]
        assert {q["code"] for q in built["items"]} == {"Q00001", "Q00002"}
        no_answers(built)


async def test_direct_history_request_uses_current_scope_after_preview(live, recommend):
    recommend.side_effect = [plan("12C11", "12C1", count=1), plan("12C4", "12C4", count=1)]
    async with chat_client(real_auth=True, seed_fn=seed_dashboard_bank) as client:
        app.dependency_overrides.pop(get_student_history)
        owner = await login_as(client, "history-direct@example.com")
        await set_grade(client)
        first = await add_draft(client, owner)
        for _ in range(2):
            await grade(client, first)
        sid = await new_session(client, None)
        _, original, _ = await say(client, sid, "Tạo đề ôn tiếp 1 câu thông hiểu")
        assert original["structure"]["rows"][0]["chapter"] == "12C11"

        await grade(client, first, correct=True)
        second = await add_draft(client, owner, chapter="12C4")
        for _ in range(2):
            await grade(client, second)
        _, updated, _ = await say(client, sid, "Làm đề ôn tiếp 1 câu thông hiểu nhé")
        assert updated["structure"]["rows"][0]["chapter"] == "12C4"
        live.assert_not_awaited()
        assert recommend.call_args.args[0]["selected_chapters"] == []


@pytest.mark.skipif(os.getenv("EXAMIND_CP3_LIVE") != "1", reason="opt-in provider validation")
async def test_history_with_configured_provider(monkeypatch, caplog):
    settings = get_settings()
    assert settings.openai_api_key and settings.openai_api_key.get_secret_value(), "Configure the backend model key"
    monkeypatch.setattr(settings, "exam_chat_live", True)
    caplog.set_level(logging.INFO, logger="app.service.exam_chat_model")
    caplog.set_level(logging.INFO, logger="app.usecase.live_exam_chat")
    text = "Tạo đề ôn tiếp 1 câu thông hiểu"
    async with chat_client(real_auth=True, seed_fn=seed_dashboard_bank) as client:
        app.dependency_overrides.pop(get_student_history)
        first = await login_as(client, "provider-first@example.com")
        await set_grade(client)
        first_chat = await new_session(client, None)
        first_draft = await add_draft(client, first)
        for _ in range(2):
            await grade(client, first_draft)
        message, preview, _ = await say(client, first_chat, text)
        assert preview is not None, message
        assert preview["structure"]["chapters"] == [{"code": "12C11", "count": 1}]
        assert "sai 6/6" in message
        edited = await client.patch(f"{BASE}/sessions/{first_chat}/preview", json={
            "version": preview["version"], "edit": {"rows": [{**preview["structure"]["rows"][0], "count": 2}]},
        })
        assert edited.status_code == 200
        draft = (await confirm(client, first_chat, edited.json()["version"])).json()["draft"]
        assert len(draft["items"]) == 2
        no_answers(draft)
        cookies = Cookies(client.cookies)

        second = await login_as(client, "provider-second@example.com")
        await set_grade(client)
        second_chat = await new_session(client, None)
        second_draft = await add_draft(client, second, chapter="12C4")
        for _ in range(2):
            await grade(client, second_draft)
        message, preview, _ = await say(client, second_chat, text)
        assert preview is not None, message
        assert preview["structure"]["chapters"] == [{"code": "12C4", "count": 1}]
        assert "sai 6/6" in message

        client.cookies.clear()
        client.cookies.update(cookies)
        await grade(client, first_draft, correct=True)
        newer_draft = await add_draft(client, first, chapter="12C4")
        for _ in range(2):
            await grade(client, newer_draft)
        message, preview, _ = await say(client, first_chat, text)
        assert preview is not None, message
        assert preview["structure"]["chapters"] == [{"code": "12C4", "count": 1}]
        assert "sai 6/6" in message
    calls = [record for record in caplog.records if record.name == "app.service.exam_chat_model"
             and record.msg.startswith("exam_chat recommendation model=")]
    assert len(calls) == 3
    assert all(record.args[1] > 0 and record.args[2] > 0 for record in calls)
