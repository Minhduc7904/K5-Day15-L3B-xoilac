"""API admin ngân hàng câu hỏi /api/v1/admin/questions (#11)."""
import pytest
from sqlalchemy import select

from app.repositories.question_bank_repository import QuestionBankRepository, available_questions, questions
from tests.admin_bank_support import admin_headers, build_db, student_headers
from tests.test_auth import API

BASE = f"{API}/admin/questions"


@pytest.fixture
async def db():
    engine, maker = await build_db()
    yield maker
    await engine.dispose()


@pytest.fixture
async def admin(client, db):
    return await admin_headers(client, db)


def body(**over):
    data = {"content": "Cau moi $x^2$", "type": "SINGLE_CHOICE", "difficulty": "TH",
            "statements": [{"content": "A1", "is_correct": True}, {"content": "B1", "is_correct": False}],
            "chapter_ids": [3]}
    return {**data, **over}


# ---- quyền -------------------------------------------------------------------------------------------------

async def test_guest_401_student_403(client):
    r = await client.get(BASE)
    assert r.status_code == 401 and r.json()["code"] == "SESSION_MISSING"
    student = await student_headers(client)
    for method, path in [("get", BASE), ("get", f"{BASE}/1"), ("post", f"{BASE}/1/archive")]:
        r = await getattr(client, method)(path, headers=student)
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"
    r = await client.post(BASE, json=body(), headers=student)
    assert r.status_code == 403


async def test_not_found_404(client, admin):
    for method, path in [("get", f"{BASE}/999"), ("post", f"{BASE}/999/archive"), ("post", f"{BASE}/999/restore")]:
        r = await getattr(client, method)(path, headers=admin)
        assert r.status_code == 404 and r.json() == {"detail": "Không có câu hỏi này", "code": "QUESTION_NOT_FOUND"}
    r = await client.put(f"{BASE}/999", json=body(), headers=admin)
    assert r.status_code == 404


# ---- danh sách, tìm, lọc -----------------------------------------------------------------------------------

async def test_list_search_and_filters(client, admin):
    r = await client.get(BASE, headers=admin)
    assert r.status_code == 200
    page = r.json()
    assert page["total"] == 4 and [i["question_id"] for i in page["items"]] == [4, 3, 2, 1]
    assert page["items"][3]["code"] == "Q00001" and page["items"][3]["chapters"][0]["code"] == "12C11"

    async def ids(**params):
        res = await client.get(BASE, params=params, headers=admin)
        assert res.status_code == 200, res.text
        return [i["question_id"] for i in res.json()["items"]]

    assert await ids(q="DONG BIEN") == [1]                   # ILIKE không phân biệt hoa thường
    assert await ids(q="Q00003") == [3]                      # tìm theo mã câu
    assert await ids(grade=11) == [3]
    assert await ids(type="TRUE_FALSE") == [2]
    assert await ids(difficulty="VDC") == [4]
    assert await ids(status="DRAFT") == [4]
    assert await ids(chapter_id=1) == [4, 2, 1]              # 12C1 gồm chương con 12C11 và cháu 12C111
    assert await ids(chapter_id=2) == [2, 1]
    assert await ids(chapter_id=1, difficulty="VD") == [2]
    two = (await client.get(BASE, params={"page": 2, "page_size": 3}, headers=admin)).json()
    assert two["total"] == 4 and [i["question_id"] for i in two["items"]] == [1]
    assert (await client.get(BASE, params={"page_size": 101}, headers=admin)).status_code == 422


async def test_detail_has_answer_solution_and_exam_count(client, admin):
    d = (await client.get(f"{BASE}/1", headers=admin)).json()
    assert d["correct_answer"] == "A" and d["exam_count"] == 1 and d["status"] == "PUBLISHED"
    assert [s["is_correct"] for s in d["statements"]] == [True, False]


# ---- tạo và sửa --------------------------------------------------------------------------------------------

async def test_create_valid_per_type(client, admin):
    r = await client.post(BASE, json=body(content="Co anh ![h](media:10)", solution="Loi giai"), headers=admin)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["grade"] == 12 and d["correct_answer"] == "A" and d["media_ids"] == [10]  # khối suy từ chương 12C12
    assert d["status"] == "PUBLISHED" and d["chapters"][0]["code"] == "12C12"

    multi = body(type="MULTIPLE_CHOICE", statements=[{"content": "x", "is_correct": True},
                                                     {"content": "y", "is_correct": False},
                                                     {"content": "z", "is_correct": True}])
    assert (await client.post(BASE, json=multi, headers=admin)).json()["correct_answer"] == "AC"
    tf = body(type="TRUE_FALSE", statements=[{"content": "a", "is_correct": True}, {"content": "b"}])
    assert (await client.post(BASE, json=tf, headers=admin)).json()["correct_answer"] == "ĐS"
    short = body(type="SHORT_ANSWER", statements=[], correct_answer="3,5", chapter_ids=[4])
    created = (await client.post(BASE, json=short, headers=admin)).json()
    assert created["grade"] == 11 and created["correct_answer"] == "3,5"
    found = (await client.get(BASE, params={"q": "cau moi"}, headers=admin)).json()  # searchable_content làm mới
    assert found["total"] == 3                                  # 3 câu "Cau moi" vừa tạo


@pytest.mark.parametrize("over, message", [
    ({"statements": [{"content": "a", "is_correct": True}, {"content": "b", "is_correct": True}]}, "đúng 1"),
    ({"statements": [{"content": "a"}, {"content": "b"}]}, "đúng 1"),
    ({"statements": [{"content": "a", "is_correct": True}]}, "ít nhất 2"),
    ({"type": "MULTIPLE_CHOICE", "statements": [{"content": "a"}, {"content": "b"}]}, "ít nhất 1 lựa chọn đúng"),
    ({"type": "TRUE_FALSE", "statements": []}, "mệnh đề"),
    ({"type": "SHORT_ANSWER", "statements": []}, "cần đáp án"),
    ({"chapter_ids": [999]}, "Không có chương"),
    ({"chapter_ids": [3, 4]}, "cùng một khối"),
    ({"grade": 10}, "không khớp"),
    ({"content": "anh ![x](media:77)"}, "media:77"),
])
async def test_create_invalid_422(client, admin, over, message):
    r = await client.post(BASE, json=body(**over), headers=admin)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "INVALID_QUESTION" and message in r.json()["detail"]


async def test_schema_errors_422(client, admin):
    assert (await client.post(BASE, json=body(content=" "), headers=admin)).status_code == 422
    assert (await client.post(BASE, json=body(chapter_ids=[]), headers=admin)).status_code == 422
    assert (await client.post(BASE, json=body(type="ABC"), headers=admin)).status_code == 422


async def test_update_keeps_statement_ids_and_replaces_chapters(client, admin):
    edit = body(content="Da sua", chapter_ids=[2, 3], statements=[
        {"statement_id": 1, "content": "(0; 2) sua", "is_correct": False},
        {"content": "moi", "is_correct": True}])
    r = await client.put(f"{BASE}/1", json=edit, headers=admin)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["content"] == "Da sua" and d["correct_answer"] == "B"
    assert [s["statement_id"] for s in d["statements"]][0] == 1 and len(d["statements"]) == 2
    assert {c["code"] for c in d["chapters"]} == {"12C11", "12C12"}
    assert d["exam_count"] == 1                                   # liên kết đề cũ giữ nguyên
    foreign = body(statements=[{"statement_id": 3, "content": "x", "is_correct": True}, {"content": "y"}])
    r = await client.put(f"{BASE}/1", json=foreign, headers=admin)
    assert r.status_code == 422 and "không thuộc" in r.json()["detail"]


# ---- lưu trữ / khôi phục -----------------------------------------------------------------------------------

async def test_archive_restore_and_selection(client, admin, db):
    r = await client.post(f"{BASE}/1/archive", headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "ARCHIVED" and r.json()["archived_at"]
    first = r.json()["archived_at"]
    assert (await client.post(f"{BASE}/1/archive", headers=admin)).json()["archived_at"] == first  # giữ mốc cũ
    archived = (await client.get(BASE, params={"status": "ARCHIVED"}, headers=admin)).json()
    assert [i["question_id"] for i in archived["items"]] == [1]
    published = (await client.get(BASE, params={"status": "PUBLISHED"}, headers=admin)).json()
    assert 1 not in [i["question_id"] for i in published["items"]]
    detail = (await client.get(f"{BASE}/1", headers=admin)).json()     # vẫn đọc được, liên kết đề còn
    assert detail["exam_count"] == 1 and len(detail["statements"]) == 2

    async with db() as s:
        avail = set((await s.execute(select(questions.c.question_id).where(available_questions()))).scalars())
        assert avail == {2, 3}
        picked = await QuestionBankRepository(s).pick_for_section(
            question_type="SINGLE_CHOICE", n=10, chapter_codes=["12C1"])
        assert picked.question_ids == []                              # #4 không chọn câu đã lưu trữ
        assert set(await QuestionBankRepository(s).load_items([1])) == {1}   # đề cũ vẫn đọc được

    r = await client.post(f"{BASE}/1/restore", headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "PUBLISHED" and r.json()["archived_at"] is None
    async with db() as s:
        picked = await QuestionBankRepository(s).pick_for_section(
            question_type="SINGLE_CHOICE", n=10, chapter_codes=["12C1"])
        assert picked.question_ids == [1]


# ---- ảnh ---------------------------------------------------------------------------------------------------

async def test_upload_and_read_image(client, admin):
    png = b"\x89PNG\r\n\x1a\nfake"
    r = await client.post(f"{BASE}/media", files={"file": ("h.png", png, "image/png")}, headers=admin)
    assert r.status_code == 201, r.text
    media_id = r.json()["media_id"]
    got = await client.get(f"{BASE}/media/{media_id}", headers=admin)
    assert got.status_code == 200 and got.content == png and got.headers["content-type"] == "image/png"
    bad = await client.post(f"{BASE}/media", files={"file": ("a.txt", b"x", "text/plain")}, headers=admin)
    assert bad.status_code == 422 and bad.json()["code"] == "INVALID_MEDIA"
    missing = await client.get(f"{BASE}/media/10", headers=admin)    # có dòng media nhưng tệp không có trong kho
    assert missing.status_code == 404 and missing.json()["code"] == "MEDIA_NOT_FOUND"
