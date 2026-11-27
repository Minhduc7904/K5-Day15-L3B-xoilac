"""Trọn luồng với hệ thống thật: đăng nhập thật (Auth #8) và tra mẫu thật (#5), không thay phụ thuộc nào.

Admin tạo và duyệt mẫu qua API #5; học sinh đăng nhập và chat ôn theo kỳ thi ở #4. Mẫu ở đây là mẫu thử.
"""
import re

import pytest

from tests.exam_chat_support import BASE, chat_client, login_as, new_session, no_answers, say

TEMPLATES = "/api/v1/exam-templates"
CK1_12 = {
    "name": "Cuối kỳ 1 lớp 12 (mẫu thử)", "exam_type": "CK1", "grade": 12, "duration_minutes": 90,
    "sections": [
        {"order": 1, "title": "Phần I. Trắc nghiệm", "question_type": "SINGLE_CHOICE", "count": 6,
         "points_per_question": 0.25, "difficulty_distribution": {"TH": 4, "VD": 2}, "chapter_codes": ["12C1", "12C4"]},
        {"order": 2, "title": "Phần II. Đúng sai", "question_type": "TRUE_FALSE", "count": 2,
         "chapter_codes": ["12C1"]},
    ],
}


@pytest.fixture
async def app_client():
    async with chat_client(real_auth=True, real_templates=True) as c:
        yield c


async def test_exam_chat_requires_student_login(app_client):
    c = app_client
    r = await c.post(f"{BASE}/sessions", json={})
    assert r.status_code == 401                                       # chưa đăng nhập

    await login_as(c, "admin-chat@example.com", "admin")
    r = await c.post(f"{BASE}/sessions", json={})
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"   # admin không dùng chat học sinh

    user_id = await login_as(c, "hs-a@example.com")
    r = await c.post(f"{BASE}/sessions", json={"student_ref": "HS99"})
    assert r.status_code == 201
    assert r.json()["student_ref"] == f"U{user_id}"                  # lấy từ tài khoản, không mạo danh được


async def test_student_only_sees_own_session_with_real_login(app_client):
    c = app_client
    await login_as(c, "hs-owner@example.com")
    sid = await new_session(c, student=None)
    await say(c, sid, "Đổi sang chương 12C4, 4 câu")

    await login_as(c, "hs-other@example.com")
    assert (await c.get(f"{BASE}/sessions/{sid}")).status_code == 404
    r = await c.post(f"{BASE}/sessions/{sid}/messages", json={"text": "xác nhận"})
    assert r.status_code == 404 and "text/event-stream" not in r.headers.get("content-type", "")


async def test_admin_approves_template_then_student_builds_exam(app_client):
    c = app_client
    await login_as(c, "admin-tpl@example.com", "admin")
    tid = (await c.post(TEMPLATES, json=CK1_12)).json()["template_id"]

    await login_as(c, "hs-tpl@example.com")
    sid = await new_session(c, student=None)
    reply, preview, _ = await say(c, sid, "Em muốn ôn thi cuối kỳ 1 lớp 12")
    assert "chưa có cấu trúc đã xác thực" in reply and preview is None   # mẫu nháp: học sinh không thấy

    await login_as(c, "admin-tpl-2@example.com", "admin")
    assert (await c.put(f"{TEMPLATES}/{tid}", json={**CK1_12, "source": "Ma trận thử"})).status_code == 200
    assert (await c.post(f"{TEMPLATES}/{tid}/approve")).json()["status"] == "APPROVED"

    await login_as(c, "hs-tpl-2@example.com")
    sid = await new_session(c, student=None)
    reply, preview, _ = await say(c, sid, "Em muốn ôn thi cuối kỳ 1 lớp 12")
    assert preview["mode"] == "EXAM_TEMPLATE" and preview["structure"]["template_id"] == tid
    assert not re.search(r"Q\d{5}", reply)

    reply, preview, draft = await say(c, sid, "xác nhận")
    assert preview["status"] == "BUILT"
    assert draft["title"].startswith("Đề ôn luyện ngày")
    assert [i["type"] for i in draft["items"]] == ["SINGLE_CHOICE"] * 6 + ["TRUE_FALSE"] * 2
    assert [i["section_title"] for i in draft["items"]][::6] == ["Phần I. Trắc nghiệm", "Phần II. Đúng sai"]
    assert draft["shortages"] == []
    no_answers(draft)


async def test_admin_edit_of_approved_template_applies_to_next_chat(app_client):
    c = app_client
    await login_as(c, "admin-edit@example.com", "admin")
    body = {**CK1_12, "source": "Ma trận thử"}
    tid = (await c.post(TEMPLATES, json=body)).json()["template_id"]
    await c.post(f"{TEMPLATES}/{tid}/approve")
    body["sections"] = [body["sections"][1]]                         # admin bỏ phần trắc nghiệm
    assert (await c.put(f"{TEMPLATES}/{tid}", json=body)).json()["status"] == "APPROVED"

    await login_as(c, "hs-edit@example.com")
    sid = await new_session(c, student=None)
    _, preview, _ = await say(c, sid, "ôn thi cuối kỳ 1 lớp 12")
    assert [s["title"] for s in preview["structure"]["sections"]] == ["Phần II. Đúng sai"]
