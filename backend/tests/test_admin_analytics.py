"""API phân tích cho dashboard admin /api/v1/admin/stats/{overview,growth,learning,bank,operations}.

Dữ liệu là học sinh, câu hỏi và lượt làm bài tự dựng. Chương và câu lấy từ tests/admin_bank_support.SEED:
12C1 > 12C11 > 12C111; 11C1; câu 1 (TH, 12C11), 2 (VD, 12C111), 3 (NB, 11C1) đã đăng, câu 4 (VDC, 12C1) là nháp.
"""
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.exam_attempt import ExamAttempt
from app.models.exam_chat import ExamChatSession, ExamDraft
from app.models.pdf_import import PdfDraft, PdfImport
from app.usecase import admin_analytics as aa
from tests.admin_bank_support import admin_headers, build_db, student_headers
from tests.test_auth import API, register

BASE = f"{API}/admin/stats"
ENDPOINTS = ("overview", "growth", "learning", "bank", "operations")

CATALOG = {
    "12C1": {"name": "Ung dung dao ham", "parent_code": None, "grade": 12},
    "12C11": {"name": "Tinh don dieu", "parent_code": "12C1", "grade": 12},
    "12C12": {"name": "Cuc tri", "parent_code": "12C1", "grade": 12},
    "12C111": {"name": "Xet dau dao ham", "parent_code": "12C11", "grade": 12},
    "11C1": {"name": "Luong giac", "parent_code": None, "grade": 11},
}


@pytest.fixture
async def db():
    engine, maker = await build_db()
    yield maker
    await engine.dispose()


@pytest.fixture
async def admin(client, db):
    return await admin_headers(client, db)


# ---- hàm thuần -------------------------------------------------------------------------------------------


def test_score_bins_edges():
    bins = aa.score_bins([0, 0.99, 1, 9.99, 10])
    assert [b["count"] for b in bins] == [2, 1, 0, 0, 0, 0, 0, 0, 0, 2]
    assert bins[0]["label"] == "0–1" and bins[9]["label"] == "9–10"


def test_top_chapter_walks_to_root_and_keeps_unknown_code():
    assert aa.top_chapter("12C111", CATALOG) == "12C1"
    assert aa.top_chapter("11C1", CATALOG) == "11C1"
    assert aa.top_chapter("99X", CATALOG) == "99X"
    assert aa.top_chapter(None, CATALOG) is None


def test_shortage_stats_groups_by_root_and_skips_full_cells():
    drafts = [
        [{"chapter": "12C111", "difficulty": "VD", "requested": 3, "available": 1},
         {"chapter": "11C1", "difficulty": "NB", "requested": 2, "available": 2}],
        [{"chapter": "12C11, 12C12", "difficulty": "TH", "requested": 2, "available": 0}],
        [],
    ]
    result = aa.shortage_stats(drafts, CATALOG)
    assert (result["drafts"], result["drafts_with_shortage"]) == (3, 2)
    top = {c["code"]: (c["missing"], c["occurrences"]) for c in result["chapters"]}
    assert top == {"12C1": (2 + 2 + 2, 3)}  # 12C111 thiếu 2; "12C11, 12C12" thiếu 2 cho mỗi mã, cùng gốc 12C1 → cộng dồn


def test_import_success_rate_ignores_in_flight():
    assert aa.import_success_rate([]) is None
    assert aa.import_success_rate([("queued", "upload", None), ("processing", "ocr", None)]) is None
    rows = [("ready_for_review", "review", None), ("failed", "ocr", None), ("queued", "upload", None)]
    assert aa.import_success_rate(rows) == 0.5


def test_trailing_active_counts_user_once_per_window():
    days = [date(2026, 11, 20) + timedelta(days=i) for i in range(10)]
    pairs = [(1, days[0]), (1, days[1]), (2, days[8])]
    wau = aa.trailing_active(days, pairs, 7)
    assert wau[0] == 1 and wau[6] == 1 and wau[7] == 1  # user 1 còn trong cửa sổ tới ngày thứ 8 (index 6)
    assert wau[8] == 1 and wau[9] == 1


# ---- API -------------------------------------------------------------------------------------------------


async def seed(client, db):
    """2 học sinh, 5 lượt chấm xong, 1 phiên chat có đề nháp thiếu câu, 3 lượt nhập PDF, 2 bản nháp PDF chờ duyệt."""
    ids = []
    for email in ("a@example.com", "b@example.com"):
        ids.append((await register(client, email=email)).json()["user_id"])
        client.cookies.clear()
    now = datetime.now(UTC)
    async with db() as s:
        chat = ExamChatSession(user_id=ids[0], student_ref=f"U{ids[0]}")
        s.add(chat)
        await s.flush()
        draft = ExamDraft(
            session_id=chat.session_id, preview_version=1, title="De thu", structure={}, items=[],
            shortages=[{"chapter": "12C111", "difficulty": "VD", "requested": 3, "available": 1}],
        )
        s.add(draft)
        await s.flush()
        items = [{"code": "Q00001", "chapter_codes": ["12C11"]}, {"code": "Q00002", "chapter": "12C111"}]
        result = {"score": 7.5, "results": [{"code": "Q00001", "status": "correct"},
                                            {"code": "Q00002", "status": "wrong"}]}
        for i in range(5):
            s.add(ExamAttempt(
                user_id=ids[0], draft_id=draft.draft_id, started_at=now - timedelta(hours=2, minutes=i),
                finished_at=now - timedelta(hours=1), graded_at=now - timedelta(hours=1), status="graded",
                reason="manual", revision=1, snapshot={"items": items}, key={}, progress={}, result=result,
            ))
        for status, stage in (("ready_for_review", "review"), ("failed", "ocr"), ("queued", "upload")):
            s.add(PdfImport(original_media_id=1, filename="a.pdf", page_count=2, status=status, stage=stage,
                            pages=[], warnings=[]))
        await s.flush()
        imp = (await s.execute(PdfImport.__table__.select().limit(1))).first()
        for position in (1, 2):
            s.add(PdfDraft(import_id=imp.id, position=position, status="pending", payload={}))
        await s.commit()
    return ids


async def kpis(client, admin, days=30):
    body = (await client.get(f"{BASE}/overview", params={"range": days}, headers=admin)).json()
    return body, {k["key"]: k for k in body["kpis"]}


async def test_guest_401_student_403_and_range_validated(client, admin):
    for name in ENDPOINTS:
        assert (await client.get(f"{BASE}/{name}")).status_code == 401
    student = await student_headers(client)
    for name in ENDPOINTS:
        r = await client.get(f"{BASE}/{name}", headers=student)
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"
        assert (await client.get(f"{BASE}/{name}", params={"range": 14}, headers=admin)).status_code == 422


async def test_empty_database_returns_zeros_not_errors(client, admin):
    for name in ENDPOINTS:
        r = await client.get(f"{BASE}/{name}", headers=admin)
        assert r.status_code == 200, (name, r.text)
    body, by_key = await kpis(client, admin)
    assert by_key["average_score"]["value"] is None and by_key["import_success_rate"]["value"] is None
    assert body["range_days"] == 30 and body["generated_at"].endswith("Z")
    learning = (await client.get(f"{BASE}/learning", headers=admin)).json()
    assert learning["graded"] == 0 and learning["median"] is None and learning["chapters"] == []


async def test_overview_kpis_and_attention(client, db, admin):
    await seed(client, db)
    body, k = await kpis(client, admin)
    assert k["completed_attempts"]["value"] == 5 and k["completed_attempts"]["previous"] == 0
    assert k["average_score"]["value"] == 7.5
    assert k["published_questions"]["value"] == 3
    assert k["new_students"]["value"] == 2  # tài khoản admin của fixture không tính là học sinh
    assert len(k["active_students"]["series"]) == 30
    assert k["import_success_rate"]["value"] == 0.5
    assert body["attention"] == {"pending_pdf_drafts": 2, "draft_questions": 1, "failed_imports": 1}


async def test_growth_funnel_is_nested_and_heatmap_counts_attempt_starts(client, db, admin):
    await seed(client, db)
    body = (await client.get(f"{BASE}/growth", params={"range": 30}, headers=admin)).json()
    assert len(body["days"]) == 30 == len(body["dau"]) == len(body["wau"]) == len(body["signups"])
    funnel = {s["key"]: s["count"] for s in body["funnel"]}
    assert funnel["registered"] == 2 and funnel["verified"] == 2
    assert funnel["profile"] == 0 and funnel["attempted"] == 0  # chưa ai hoàn tất hồ sơ, các bước sau cũng về 0
    assert sum(map(sum, body["heatmap"])) == 5 and len(body["heatmap"]) == 7 and len(body["heatmap"][0]) == 24
    assert body["dau"][-1] >= 1 and body["active_students"] >= 1
    assert [g["key"] for g in body["grades"]] == ["10", "11", "12"]


async def test_learning_distribution_and_hardest_chapters(client, db, admin):
    await seed(client, db)
    body = (await client.get(f"{BASE}/learning", params={"range": 30}, headers=admin)).json()
    assert body["graded"] == 5 and body["median"] == 7.5 and body["average"] == 7.5
    assert body["bins"][7]["count"] == 5 and sum(b["count"] for b in body["bins"]) == 5
    assert sum(w["manual"] for w in body["outcomes"]) == 5 and sum(w["timeout"] for w in body["outcomes"]) == 0
    assert body["chapters"] == [{"code": "12C1", "name": "Ung dung dao ham", "correct": 5, "total": 10, "rate": 0.5}]
    assert body["min_answers"] == 5


async def test_bank_coverage_and_shortages(client, db, admin):
    await seed(client, db)
    body = (await client.get(f"{BASE}/bank", params={"range": 30}, headers=admin)).json()
    assert (body["published"], body["draft"], body["archived"]) == (3, 1, 0)
    cover = {row["code"]: row for row in body["coverage"]}
    assert cover["12C1"]["counts"] == {"NB": 0, "TH": 1, "VD": 1, "VDC": 0}  # câu nháp VDC không tính
    assert cover["11C1"]["counts"]["NB"] == 1 and cover["11C1"]["total"] == 1
    assert body["shortages"]["drafts"] == 1 and body["shortages"]["drafts_with_shortage"] == 1
    assert body["shortages"]["chapters"] == [
        {"code": "12C1", "name": "Ung dung dao ham", "missing": 2, "occurrences": 1}]
    assert {d["key"]: d["count"] for d in body["by_difficulty"]} == {"NB": 1, "TH": 1, "VD": 1, "VDC": 0}


async def test_operations_imports_credits_and_chat_conversion(client, db, admin):
    await seed(client, db)
    body = (await client.get(f"{BASE}/operations", params={"range": 30}, headers=admin)).json()
    imports = body["imports"]
    assert imports["total"] == 3 and imports["success_rate"] == 0.5
    assert imports["failed_by_stage"] == [{"key": "ocr", "count": 1}]
    assert sum(imports["completed"]) == 1 and sum(imports["failed"]) == 1 and sum(imports["in_flight"]) == 1
    assert body["pdf_drafts"] == {"pending": 2}
    assert sum(body["credits"]["granted"]) >= 0 and len(body["credits"]["spent"]) == 30
    assert body["chat"]["sessions"] == 1 and body["chat"]["with_draft"] == 1 and body["chat"]["with_attempt"] == 1
