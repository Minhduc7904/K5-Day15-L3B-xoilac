"""Test quyền sở hữu phiên chat (issue #4). Giả lập người đăng nhập bằng cách thay get_requester().

Khi Auth #8 merge, get_requester() lấy học sinh từ phiên đăng nhập; các luật dưới đây giữ nguyên.
"""
import pytest

from app.usecase.exam_chat import Requester
from tests.exam_chat_support import BASE, Holder, chat_client, new_session, say

ALICE = Requester(user_id=1, student_ref="U1")
BOB = Requester(user_id=2, student_ref="U2")


@pytest.fixture
async def ctx():
    who = Holder()
    async with chat_client(requester=who) as c:
        yield c, who


async def test_logged_in_student_owns_new_session(ctx):
    chat, who = ctx
    who.value = ALICE
    r = await chat.post(f"{BASE}/sessions", json={})
    assert r.status_code == 201
    assert r.json()["student_ref"] == "U1"                         # lấy từ người đăng nhập, không từ body

    forged = await chat.post(f"{BASE}/sessions", json={"student_ref": "U2"})
    assert forged.json()["student_ref"] == "U1"                    # không mạo danh được học sinh khác


async def test_other_student_cannot_see_or_use_session(ctx):
    chat, who = ctx
    who.value = ALICE
    sid = await new_session(chat, student=None)
    _, preview, _ = await say(chat, sid, "Đổi sang chương 12C4, 4 câu")
    version = preview["version"]

    who.value = BOB
    calls = [
        chat.get(f"{BASE}/sessions/{sid}"),
        chat.post(f"{BASE}/sessions/{sid}/messages", json={"text": "xác nhận"}),
        chat.get(f"{BASE}/sessions/{sid}/preview"),
        chat.patch(f"{BASE}/sessions/{sid}/preview", json={"version": version, "edit": {"total": 2}}),
        chat.post(f"{BASE}/sessions/{sid}/preview/confirm", json={"version": version}),
        chat.get(f"{BASE}/sessions/{sid}/draft"),
    ]
    for call in calls:
        r = await call
        assert r.status_code == 404, r.text                         # như không tồn tại, không lộ phiên của người khác
        assert "text/event-stream" not in r.headers.get("content-type", "")

    who.value = ALICE                                               # chủ phiên vẫn dùng bình thường, không bị Bob đổi
    state = (await chat.get(f"{BASE}/sessions/{sid}")).json()
    assert state["preview"]["version"] == version
    assert [m["role"] for m in state["messages"]] == ["student", "assistant"]
    r = await chat.post(f"{BASE}/sessions/{sid}/preview/confirm", json={"version": version})
    assert r.status_code == 200 and r.json()["draft"] is not None


async def test_session_created_before_login_is_not_exposed(ctx):
    chat, who = ctx
    who.value = None
    sid = await new_session(chat, student="HS01")                   # phiên tạo khi chưa có Auth: user_id NULL
    who.value = ALICE
    assert (await chat.get(f"{BASE}/sessions/{sid}")).status_code == 404


async def test_without_login_student_ref_is_required(ctx):
    chat, who = ctx
    who.value = None
    r = await chat.post(f"{BASE}/sessions", json={})
    assert r.status_code == 422
    assert (await chat.post(f"{BASE}/sessions", json={"student_ref": "HS01"})).status_code == 201


async def test_rename_and_delete_session_owner_only_and_keeps_draft(ctx):
    chat, who = ctx
    who.value = ALICE
    sid = await new_session(chat, student=None)
    _, _, draft = await say(chat, sid, "Xác nhận cấu trúc: chương 12C1, 5 câu (3 thông hiểu, 2 vận dụng). Tạo đề nháp.")
    assert draft is not None

    renamed = await chat.patch(f"{BASE}/sessions/{sid}", json={"title": "  Ôn đạo hàm  "})
    assert renamed.status_code == 200 and renamed.json()["title"] == "Ôn đạo hàm"
    listed = (await chat.get(f"{BASE}/sessions")).json()
    assert [item["title"] for item in listed if item["session_id"] == sid] == ["Ôn đạo hàm"]
    assert (await chat.patch(f"{BASE}/sessions/{sid}", json={"title": "   "})).status_code == 422

    who.value = BOB                                                 # người khác không đổi tên, không xoá được
    assert (await chat.patch(f"{BASE}/sessions/{sid}", json={"title": "x"})).status_code == 404
    assert (await chat.delete(f"{BASE}/sessions/{sid}")).status_code == 404

    who.value = ALICE
    assert (await chat.delete(f"{BASE}/sessions/{sid}")).status_code == 204
    assert sid not in [item["session_id"] for item in (await chat.get(f"{BASE}/sessions")).json()]
    assert (await chat.get(f"{BASE}/sessions/{sid}")).status_code == 404
    assert (await chat.delete(f"{BASE}/sessions/{sid}")).status_code == 404
    # Đề đã dựng vẫn còn trong "Đề của tôi".
    assert draft["draft_id"] in [d["draft_id"] for d in (await chat.get(f"{BASE}/drafts")).json()]
