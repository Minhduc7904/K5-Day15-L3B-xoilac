"""Live API contracts with a deterministic substitute for the model transport."""
import asyncio
import os
from unittest.mock import AsyncMock

import pytest

from app.core.config import get_settings
from app.service.exam_chat_model import ChatAction, ExamChatModel
from tests.exam_chat_support import BASE, chat_client, login_as, new_session, no_answers, say

PROFILE = "/api/v1/student/me/profile"
CREDITS = "/api/v1/student/me/credits"


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(get_settings(), "exam_chat_live", True)
    actions = AsyncMock()
    monkeypatch.setattr(ExamChatModel, "interpret", lambda _self, context: actions(context))
    monkeypatch.setattr(ExamChatModel, "summarize", lambda _self, prior, messages: asyncio.sleep(0, result="Tóm tắt cũ"))
    return actions


async def confirm(client, sid, version, count=None):
    return await client.post(f"{BASE}/sessions/{sid}/preview/confirm",
                             json={"version": version, "accepted_count": count})


async def test_tool_dispatch_uses_function_schema(monkeypatch):
    model = ExamChatModel(get_settings())
    response = {"tool_calls": [{"function": {"name": "replace", "arguments": '{"question_orders":[3]}'}}]}
    call = AsyncMock(return_value=response)
    monkeypatch.setattr(model, "_call", call)
    action = await model.interpret({"request": "Thay giúp câu ba"})
    assert action.action == "replace" and action.question_orders == [3]
    options = call.call_args.kwargs
    assert options["tool_choice"] == "required"
    assert {tool["function"]["name"] for tool in options["tools"]} >= {"chapter", "template", "confirm", "replace"}


async def test_context_scope_shortage_and_free_replacement(live):
    live.side_effect = [
        ChatAction(action="chapter", chapters=["12C1"], total=5, difficulty_counts={"TH": 5}),
        ChatAction(action="edit", total=3, difficulty_counts={"TH": 3}),
        ChatAction(action="replace", question_orders=[2]),
        ChatAction(action="history"),
    ]
    async with chat_client(real_auth=True) as client:
        await login_as(client, "live@example.com")
        profile = await client.put(PROFILE, json={
            "school_name": "THPT Mẫu", "grade": 11, "target_score": 8,
            "exam_period": "final_1", "study_days": [1, 3],
        })
        assert profile.status_code == 200, profile.text
        sid = await new_session(client, None)
        _, preview, draft = await say(client, sid, "Ôn chương ứng dụng đạo hàm")
        assert not draft
        assert preview["structure"]["chapters"] == [{"code": "12C11", "count": 5}]
        context = live.call_args.args[0]
        assert context["student"] == {"grade": 11, "target_score": 8, "exam_type": "CK1"}
        assert context["catalog"]["12C11"]["parent_code"] == "12C1"
        assert "school_name" not in context["student"]
        first = (await confirm(client, sid, preview["version"])).json()
        assert first["draft"] is None and first["preview"]["offer"]["count"] == 4
        assert "ids" not in first["preview"]["offer"]
        assert (await client.get(CREDITS)).json()["balance"] == 500
        offer_version = first["preview"]["version"]
        rejected = (await confirm(client, sid, offer_version, 3)).json()
        assert rejected["draft"] is None
        accepted = (await confirm(client, sid, offer_version, 4)).json()
        first_draft = accepted["draft"]
        assert len(first_draft["items"]) == 4 and first_draft["shortages"]
        no_answers(first_draft)
        retry = (await confirm(client, sid, offer_version, 4)).json()
        assert retry["draft"]["draft_id"] == first_draft["draft_id"]
        notices = (await client.get("/api/v1/student/me/notifications")).json()
        assert [(n["kind"], n["link"]) for n in notices["items"]] == [("draft_ready", f"/exams/draft-{first_draft['draft_id']}")]

        _, preview, _ = await say(client, sid, "Bớt còn 3 để có thể thay câu sau")
        context = live.call_args.args[0]
        assert context["recent"][0]["text"] == "Ôn chương ứng dụng đạo hàm"
        assert context["draft"]["questions"][0]["code"] == "Q00001"
        revised = (await confirm(client, sid, preview["version"])).json()["draft"]
        assert revised["draft_id"] == first_draft["draft_id"]

        _, preview, _ = await say(client, sid, "Cho mình đổi câu thứ hai")
        changed = (await confirm(client, sid, preview["version"])).json()["draft"]
        original_codes = [item["code"] for item in revised["items"]]
        codes = [item["code"] for item in changed["items"]]
        assert codes == [original_codes[0], "Q00004", original_codes[2]]
        assert changed["draft_id"] == first_draft["draft_id"]
        assert len((await client.get("/api/v1/student/me/notifications")).json()["items"]) == 1  # sửa tại chỗ không báo lại
        wallet = (await client.get(CREDITS)).json()
        assert wallet["balance"] == 400
        assert [entry["delta"] for entry in wallet["history"] if entry["reason"] == "exam_creation"] == [-100]
        assert len((await client.get(f"{BASE}/drafts")).json()) == 1

        reply, _, _ = await say(client, sid, "Ôn phần em thường sai")
        assert "chưa có lịch sử" in reply
        await login_as(client, "other-live@example.com")
        assert (await client.get(f"{BASE}/drafts")).json() == []
        for path in (f"/sessions/{sid}/transcript", f"/drafts/{changed['draft_id']}",
                     f"/drafts/{changed['draft_id']}/media/123"):
            assert (await client.get(BASE + path)).status_code == 404


async def test_parent_distributes_fifty_and_child_stays_narrow(live):
    from sqlalchemy import insert
    from app.repositories.question_bank_repository import chapters, questions, questions_chapters
    from tests.exam_chat_support import seed

    async def seed_children(conn):
        await seed(conn)
        await conn.execute(insert(chapters), {"chapter_id": 6, "code": "12C12", "name": "Cực trị",
                                             "parent_chapter_id": 1, "level": 1})
        for i in range(60, 110):
            await conn.execute(insert(questions), {"question_id": i, "content": f"Câu thử {i}",
                                                  "type": "SINGLE_CHOICE", "difficulty": "TH",
                                                  "grade": 12, "visibility": "PUBLISHED"})
            await conn.execute(insert(questions_chapters),
                               {"question_id": i, "chapter_id": 2 if i < 85 else 6})

    live.side_effect = [
        ChatAction(action="chapter", chapters=["12C1"], total=50, difficulty_counts={"TH": 50}),
        ChatAction(action="chapter", chapters=["12C12"], total=10, difficulty_counts={"TH": 10}),
    ]
    async with chat_client(real_auth=True, seed_fn=seed_children) as client:
        await login_as(client, "fifty@example.com")
        sid = await new_session(client, None)
        _, preview, _ = await say(client, sid, "Cho 50 câu về ứng dụng đạo hàm")
        assert preview["structure"]["chapters"] == [{"code": "12C11", "count": 25}, {"code": "12C12", "count": 25}]
        oversized = await client.patch(f"{BASE}/sessions/{sid}/preview",
                                       json={"version": preview["version"], "edit": {"total": 51}})
        assert oversized.status_code == 422
        result = (await confirm(client, sid, preview["version"])).json()["draft"]
        assert len(result["items"]) == 50 and not result["shortages"]
        assert len({item["question_id"] for item in result["items"]}) == 50
        assert {item["chapter"] for item in result["items"]} == {"12C11", "12C12"}

        _, preview, _ = await say(client, sid, "Đổi sang ôn riêng cực trị")
        assert preview["structure"]["chapters"] == [{"code": "12C12", "count": 10}]
        result = (await confirm(client, sid, preview["version"])).json()["draft"]
        assert {item["chapter"] for item in result["items"]} == {"12C12"}


async def test_template_defaults_from_profile_and_rejects_over_fifty(live):
    from tests.test_exam_chat_integration import CK1_12, TEMPLATES

    live.side_effect = [
        ChatAction(action="template"),
        ChatAction(action="template", exam_type="CK1", version_label="large"),
    ]
    async with chat_client(real_auth=True, real_templates=True) as client:
        await login_as(client, "template-admin@example.com", "admin")
        small = await client.post(TEMPLATES, json={**CK1_12, "source": "Mẫu thử", "version_label": "small"})
        assert small.status_code == 201, small.text
        large = await client.post(TEMPLATES, json={
            **CK1_12, "source": "Mẫu thử", "version_label": "large",
            "sections": [{"order": 1, "title": "Phần I", "question_type": "SINGLE_CHOICE", "count": 51}],
        })
        assert large.status_code == 201, large.text
        for item in (small, large):
            approved = await client.post(f"{TEMPLATES}/{item.json()['template_id']}/approve")
            assert approved.status_code == 200, approved.text

        await login_as(client, "template-student@example.com")
        profile = await client.put(PROFILE, json={
            "school_name": "THPT Mẫu", "grade": 12, "target_score": 8,
            "exam_period": "final_1", "study_days": [1, 3],
        })
        assert profile.status_code == 200
        sid = await new_session(client, None)
        reply, preview, _ = await say(client, sid, "Cho mình đề theo kỳ thi trong hồ sơ")
        assert "nhiều mẫu" in reply and preview is None
        reply, preview, _ = await say(client, sid, "Chọn phiên bản large")
        assert "hơn 50" in reply and preview is None
        live.side_effect = None
        live.return_value = ChatAction(action="template", version_label="small", chapters=["12C11"])
        _, preview, _ = await say(client, sid, "Chọn bản small, chỉ ôn chương con tính đơn điệu")
        assert preview["structure"]["template_id"] == small.json()["template_id"]
        assert all(section["chapters"] == ["12C11"] for section in preview["structure"]["sections"])
        conflict = await client.patch(f"{BASE}/sessions/{sid}/preview",
                                      json={"version": preview["version"], "edit": {"total": 40}})
        assert conflict.status_code == 422 and conflict.json()["detail"]["code"] == "TEMPLATE_CONFLICT"
        offer = (await confirm(client, sid, preview["version"])).json()["preview"]
        result = (await confirm(client, sid, offer["version"], offer["offer"]["count"])).json()["draft"]
        assert all(item["chapter"] == "12C11" and item["subchapter_codes"] == ["12C11"] for item in result["items"])


async def test_cancel_does_not_reuse_preview_versions(live):
    chapter = ChatAction(action="chapter", chapters=["12C11"], total=1, difficulty_counts={"TH": 1})
    live.side_effect = [chapter, ChatAction(action="cancel"), chapter]
    async with chat_client(real_auth=True) as client:
        await login_as(client, "cancel@example.com")
        sid = await new_session(client, None)
        _, original, _ = await say(client, sid, "Ôn tính đơn điệu")
        _, cancelled, _ = await say(client, sid, "Bỏ bản này")
        assert cancelled is None
        assert (await client.get(f"{BASE}/sessions/{sid}/preview")).status_code == 404
        _, fresh, _ = await say(client, sid, "Lập preview mới")
        assert fresh["version"] > original["version"]
        assert (await confirm(client, sid, original["version"])).status_code == 409
        assert (await client.get(CREDITS)).json()["balance"] == 500


async def test_long_chat_preserves_older_context(live):
    live.return_value = ChatAction(action="clarify", question="Em muốn ôn chương nào?")
    async with chat_client(real_auth=True) as client:
        await login_as(client, "long@example.com")
        sid = await new_session(client, None)
        await say(client, sid, "Chủ đề tích phân đặc biệt")
        for i in range(18):
            await say(client, sid, f"Thêm ràng buộc số {i}")
        await say(client, sid, "Lấy lại chủ đề tích phân đặc biệt")
        context = live.call_args.args[0]
        assert context["summary"] == "Tóm tắt cũ"
        assert any(message["text"] == "Chủ đề tích phân đặc biệt" for message in context["past_references"])
        messages = (await client.get(f"{BASE}/sessions/{sid}/transcript?limit=2")).json()
        assert len(messages) == 2 and messages[0]["content"] == "Lấy lại chủ đề tích phân đặc biệt"


async def test_model_error_keeps_session_unmodified(live):
    from app.service.exam_chat_model import ExamChatModelError
    live.side_effect = ExamChatModelError("model unavailable")
    async with chat_client(real_auth=True) as client:
        await login_as(client, "unavailable@example.com")
        sid = await new_session(client, None)
        result = await client.post(f"{BASE}/sessions/{sid}/messages", json={"text": "Tạo đề giúp em"})
        assert result.status_code == 503
        state = (await client.get(f"{BASE}/sessions/{sid}")).json()
        assert state["messages"] == [] and state["preview"] is None and state["draft"] is None
        assert (await client.get(CREDITS)).json()["balance"] == 500


async def test_failed_draft_write_rolls_back_credit(live):
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from app.models.exam_chat import ExamDraft

    live.return_value = ChatAction(action="chapter", chapters=["12C11"], total=1, difficulty_counts={"TH": 1})

    def fail_new_draft(db, _context, _instances):
        if any(isinstance(item, ExamDraft) for item in db.new):
            raise RuntimeError("simulated draft write failure")

    async with chat_client(real_auth=True) as client:
        await login_as(client, "rollback@example.com")
        sid = await new_session(client, None)
        _, preview, _ = await say(client, sid, "Cho một câu tính đơn điệu")
        event.listen(Session, "before_flush", fail_new_draft)
        try:
            with pytest.raises(RuntimeError, match="simulated draft write failure"):
                await confirm(client, sid, preview["version"])
        finally:
            event.remove(Session, "before_flush", fail_new_draft)
        state = (await client.get(f"{BASE}/sessions/{sid}")).json()
        assert state["draft"] is None and state["preview"]["version"] == preview["version"]
        assert (await client.get(CREDITS)).json()["balance"] == 500


async def test_postgres_serializes_double_confirm_and_last_credit(live):
    url = os.environ.get("EXAM_CHAT_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requires a disposable PostgreSQL database")
    live.return_value = ChatAction(action="chapter", chapters=["12C11"], total=1, difficulty_counts={"TH": 1})
    from app.models.student import CreditAccount

    async with chat_client(real_auth=True, database_url=url) as client:
        user_id = await login_as(client, "race@example.com")
        async with client.db.begin() as db:
            account = await db.get(CreditAccount, user_id)
            account.balance = 200
        sessions = []
        for _ in range(3):
            sid = await new_session(client, None)
            _, preview, _ = await say(client, sid, "Cho một câu tính đơn điệu")
            sessions.append((sid, preview["version"]))
        results = await asyncio.gather(*(confirm(client, *sessions[0]) for _ in range(2)))
        assert [item.status_code for item in results] == [200, 200]
        assert len({item.json()["draft"]["draft_id"] for item in results}) == 1
        assert (await client.get(CREDITS)).json()["balance"] == 100
        results = await asyncio.gather(*(confirm(client, *session) for session in sessions[1:]))
        assert sorted(item.status_code for item in results) == [200, 402]
        assert len((await client.get(f"{BASE}/drafts")).json()) == 2
        wallet = (await client.get(CREDITS)).json()
        assert wallet["balance"] == 0
        assert sum(entry["delta"] for entry in wallet["history"] if entry["reason"] == "exam_creation") == -200

        first_id = (await client.get(f"{BASE}/sessions/{sessions[0][0]}/draft")).json()["draft_id"]
        live.return_value = ChatAction(action="edit", duration_minutes=30)
        sid = sessions[0][0]
        _, preview, _ = await say(client, sid, "Đổi thời lượng thành 30 phút")
        updated = await confirm(client, sid, preview["version"])
        assert updated.status_code == 200
        assert updated.json()["draft"]["draft_id"] == first_id
        assert (await client.get(CREDITS)).json()["balance"] == 0
