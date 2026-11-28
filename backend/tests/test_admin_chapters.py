"""API admin danh mục chương /api/v1/admin/chapters (#11)."""
import pytest

from tests.admin_bank_support import admin_headers, build_db, student_headers
from tests.test_auth import API

BASE = f"{API}/admin/chapters"


@pytest.fixture
async def db():
    engine, maker = await build_db()
    yield maker
    await engine.dispose()


@pytest.fixture
async def admin(client, db):
    return await admin_headers(client, db)


def find(nodes, code):
    for node in nodes:
        if node["code"] == code:
            return node
        hit = find(node["children"], code)
        if hit:
            return hit
    return None


async def test_guest_401_student_403(client):
    assert (await client.get(BASE)).status_code == 401
    student = await student_headers(client)
    for method, path, kw in [("get", BASE, {}), ("post", BASE, {"json": {"name": "x", "code": "12C9"}}),
                             ("put", f"{BASE}/1", {"json": {"name": "x", "code": "12C1"}}), ("delete", f"{BASE}/3", {})]:
        r = await getattr(client, method)(path, headers=student, **kw)
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"


async def test_tree_by_grade_with_counts(client, admin):
    r = await client.get(BASE, params={"grade": 12}, headers=admin)
    assert r.status_code == 200
    tree = r.json()
    assert [n["code"] for n in tree] == ["12C1"]
    root = tree[0]
    assert [c["code"] for c in root["children"]] == ["12C11", "12C12"]        # theo order_in_parent
    assert root["question_count"] == 1 and root["subtree_question_count"] == 3  # q4 trực tiếp, q1, q2 ở nhánh con
    assert find(tree, "12C111")["level"] == 2 and find(tree, "12C111")["grade"] == 12
    all_grades = (await client.get(BASE, headers=admin)).json()
    assert {n["code"] for n in all_grades} == {"12C1", "11C1"}


async def test_create_rename_move_and_levels(client, admin):
    r = await client.post(BASE, json={"name": "Tiem can", "code": "12C13", "parent_chapter_id": 1}, headers=admin)
    assert r.status_code == 201, r.text
    new = r.json()
    assert new["level"] == 1 and new["order_in_parent"] == 3 and new["slug"] == "12c13-tiem-can"

    r = await client.put(f"{BASE}/{new['chapter_id']}", json={"name": "Đường tiệm cận", "code": "12C13"},
                         headers=admin)
    assert r.status_code == 200 and r.json()["name"] == "Đường tiệm cận" and r.json()["parent_chapter_id"] is None
    assert r.json()["level"] == 0                                              # thành chương gốc

    # chuyển 12C11 (có con 12C111) sang dưới 12C12: cả nhánh tăng level
    r = await client.put(f"{BASE}/2", json={"name": "Tinh don dieu", "code": "12C11", "slug": "12c11",
                                            "parent_chapter_id": 3}, headers=admin)
    assert r.status_code == 200, r.text
    tree = (await client.get(BASE, params={"grade": 12}, headers=admin)).json()
    assert find(tree, "12C11")["level"] == 2 and find(tree, "12C111")["level"] == 3
    assert [c["code"] for c in find(tree, "12C12")["children"]] == ["12C11"]


async def test_duplicate_code_and_slug_409(client, admin):
    r = await client.post(BASE, json={"name": "Trung", "code": "12C11", "parent_chapter_id": 1}, headers=admin)
    assert r.status_code == 409 and r.json()["code"] == "CHAPTER_CODE_TAKEN" and "12C11" in r.json()["detail"]
    r = await client.post(BASE, json={"name": "Khac", "code": "12C19", "slug": "12c12", "parent_chapter_id": 1},
                          headers=admin)
    assert r.status_code == 409 and "Slug" in r.json()["detail"]
    r = await client.put(f"{BASE}/3", json={"name": "Cuc tri", "code": "12C11", "parent_chapter_id": 1}, headers=admin)
    assert r.status_code == 409


async def test_cycle_and_missing_parent(client, admin):
    r = await client.put(f"{BASE}/1", json={"name": "x", "code": "12C1", "parent_chapter_id": 1}, headers=admin)
    assert r.status_code == 422 and r.json()["code"] == "CHAPTER_CYCLE"
    r = await client.put(f"{BASE}/1", json={"name": "x", "code": "12C1", "parent_chapter_id": 5}, headers=admin)
    assert r.status_code == 422 and r.json()["code"] == "CHAPTER_CYCLE"        # 12C111 là cháu của 12C1
    r = await client.post(BASE, json={"name": "x", "code": "12C9", "parent_chapter_id": 999}, headers=admin)
    assert r.status_code == 404 and r.json()["code"] == "CHAPTER_NOT_FOUND"
    r = await client.put(f"{BASE}/999", json={"name": "x", "code": "12C9"}, headers=admin)
    assert r.status_code == 404


async def test_invalid_code_and_grade_rules(client, admin):
    r = await client.post(BASE, json={"name": "x", "code": "abc"}, headers=admin)
    assert r.status_code == 422 and r.json()["code"] == "INVALID_CHAPTER"
    r = await client.post(BASE, json={"name": "x", "code": "11C19", "parent_chapter_id": 1}, headers=admin)
    assert r.status_code == 422 and "cùng khối" in r.json()["detail"]
    # 12C11 có câu: đổi sang khối 11 (dưới 11C1) bị chặn
    r = await client.put(f"{BASE}/2", json={"name": "x", "code": "11C11", "parent_chapter_id": 4}, headers=admin)
    assert r.status_code == 409 and r.json()["code"] == "CHAPTER_IN_USE"


async def test_delete_rules(client, admin):
    r = await client.delete(f"{BASE}/1", headers=admin)
    assert r.status_code == 409 and r.json()["code"] == "CHAPTER_IN_USE"
    assert "2 chương con" in r.json()["detail"] and "1 câu hỏi" in r.json()["detail"]
    r = await client.delete(f"{BASE}/5", headers=admin)                         # lá nhưng còn câu q2
    assert r.status_code == 409 and "1 câu hỏi" in r.json()["detail"]
    assert (await client.delete(f"{BASE}/3", headers=admin)).status_code == 204  # 12C12: không con, không câu
    assert (await client.delete(f"{BASE}/3", headers=admin)).status_code == 404
    # câu tham chiếu chương vẫn đọc đúng
    q = (await client.get(f"{API}/admin/questions/2", headers=admin)).json()
    assert q["chapters"][0]["code"] == "12C111"
