"""Hạ tầng test dùng chung cho issue #4: SQLite trong bộ nhớ, ngân hàng câu tự dựng, client HTTP, đọc SSE.

Dữ liệu ở đây là dữ liệu thử tự dựng, không phải câu hỏi hay học sinh thật.
"""
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    get_exam_template_source,
    get_password_service,
    get_requester,
    get_student_history,
)
from app.core.config import get_settings
from app.core.database import get_session
from app.main import app
from app.models import Base
from app.repositories.question_bank_repository import chapters, content_metadata, questions, questions_chapters, statements
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.service.exam_chat_sources import NoHistory, NoTemplates
from app.service.token_service import TokenService
from app.usecase.auth import AuthUseCase
from tests.conftest import TEST_SETTINGS, new_password

BASE = "/api/v1/exam-chat"

CHAPTERS = [
    {"chapter_id": 1, "code": "12C1", "name": "ỨNG DỤNG ĐẠO HÀM", "parent_chapter_id": None, "level": 0},
    {"chapter_id": 2, "code": "12C11", "name": "Tính đơn điệu", "parent_chapter_id": 1, "level": 1},
    {"chapter_id": 3, "code": "12C4", "name": "NGUYÊN HÀM VÀ TÍCH PHÂN", "parent_chapter_id": None, "level": 0},
    {"chapter_id": 4, "code": "11C6", "name": "HÀM SỐ MŨ VÀ HÀM SỐ LÔGARIT", "parent_chapter_id": None, "level": 0},
]


def _question_rows() -> tuple[list[dict], list[dict]]:
    rows, links = [], []

    def q(qid, chapter_id, diff, qtype="SINGLE_CHOICE", visibility="PUBLISHED", grade=12):
        rows.append({"question_id": qid, "content": f"Câu thử {qid}", "type": qtype, "difficulty": diff,
                     "grade": grade, "visibility": visibility})
        links.append({"question_id": qid, "chapter_id": chapter_id})

    for qid in range(1, 5):
        q(qid, 2, "TH")                       # gắn chương con 12C11 → vẫn thuộc 12C1
    for qid in range(5, 8):
        q(qid, 1, "VD")
    q(8, 1, "NB")
    q(9, 1, "NB")
    q(10, 1, "VDC")
    q(11, 1, "TH", visibility="DRAFT")         # chưa duyệt: không bao giờ được chọn
    for qid in (20, 21, 22):
        q(qid, 3, "TH")
    q(23, 3, "VD")
    q(24, 3, "NB")
    for qid in range(30, 36):
        q(qid, 4, "TH", grade=11)
    for qid in (40, 41, 42):
        q(qid, 1, "TH", qtype="TRUE_FALSE")
    q(43, 1, "TH", qtype="TRUE_FALSE", visibility="DRAFT")
    q(50, 3, "VD", qtype="SHORT_ANSWER")
    return rows, links


async def seed(conn) -> None:
    await conn.execute(insert(chapters), CHAPTERS)
    rows, links = _question_rows()
    await conn.execute(insert(questions), rows)
    await conn.execute(insert(questions_chapters), links)
    await conn.execute(insert(statements), [
        {"statement_id": 1, "content": "A. đúng", "question_id": 1, "is_correct": True, "order": 1},
        {"statement_id": 2, "content": "B. sai", "question_id": 1, "is_correct": False, "order": 2},
    ])


class Holder:
    """Giá trị đổi được giữa các lệnh gọi trong một test (vd người đang đăng nhập)."""

    def __init__(self, value=None) -> None:
        self.value = value


@asynccontextmanager
async def chat_client(
    *,
    history=None,
    templates=None,
    requester: Holder | None = None,
    seed_fn: Callable | None = seed,
    real_auth: bool = False,
    real_templates: bool = False,
    database_url: str | None = None,
) -> AsyncIterator[AsyncClient]:
    """Client HTTP với DB riêng. Ba chế độ người gọi:

    - mặc định (test logic): bỏ qua đăng nhập, người gọi None, client gửi student_ref như trước khi có Auth;
    - requester=Holder(...): người gọi do test đặt (test luật chủ sở hữu);
    - real_auth=True: dùng đăng nhập thật của #8 (cookie phiên), tạo tài khoản bằng login_as().
    real_templates=True: tra mẫu qua ExamTemplateUseCase thật của #5 thay vì nguồn giả.
    """
    engine = (create_async_engine(database_url) if database_url else
              create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(content_metadata.create_all)
        if seed_fn is not None:
            await seed_fn(conn)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _session():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    app.dependency_overrides[get_student_history] = lambda: history or NoHistory()
    if not real_templates:
        app.dependency_overrides[get_exam_template_source] = lambda: templates or NoTemplates()
    if requester is not None:
        app.dependency_overrides[get_requester] = lambda: requester.value
    elif not real_auth:
        app.dependency_overrides[get_requester] = lambda: None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.db = maker  # để login_as() tạo tài khoản trong cùng DB
            yield c
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def login_as(c: AsyncClient, email: str, role: str = "student") -> int:
    """Tạo tài khoản (mật khẩu sinh lúc chạy, không viết cứng) rồi đăng nhập; cookie phiên giữ trong client.

    Trả user_id. Gọi lại với email khác để đổi người dùng."""
    password = new_password()
    async with c.db() as s:
        uc = AuthUseCase(UserRepository(s), SessionRepository(s), get_password_service(), TokenService(), 168)
        user = await uc.create_user(email, password, role)
    c.cookies.clear()
    r = await c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return user.user_id


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def new_session(c: AsyncClient, student: str | None = "HS01") -> int:
    r = await c.post(f"{BASE}/sessions", json={"student_ref": student} if student else {})
    assert r.status_code == 201, r.text
    return r.json()["session_id"]


async def say(c: AsyncClient, sid: int, text: str):
    """Gửi một tin nhắn, trả (câu trả lời ghép từ các delta, preview hoặc None, draft hoặc None)."""
    r = await c.post(f"{BASE}/sessions/{sid}/messages", json={"text": text})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    assert events[-1][0] == "done"
    reply = "".join(d["delta"] for e, d in events if e == "message")
    found = {e: d for e, d in events if e in ("preview", "draft")}
    return reply, found.get("preview"), found.get("draft")


def no_answers(draft: dict) -> None:
    text = json.dumps(draft, ensure_ascii=False)
    for key in ("is_correct", "correct_answer", "solution"):
        assert key not in text
