"""Test issue #5: mẫu cấu trúc đề. Dữ liệu dưới đây là mẫu tự dựng để thử luật, không phải cấu trúc đề chính thức.

Mặc định mỗi test đăng nhập bằng một admin (fixture as_admin). Test phân quyền tự đăng xuất hoặc đổi tài khoản.
Mật khẩu sinh lúc chạy (tests/conftest.py), không viết cứng.
"""
import copy

import pytest

from app.api.deps import get_password_service
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.exam_template import ExamTemplateIn
from app.service.token_service import TokenService
from app.usecase.auth import AuthUseCase
from app.usecase.exam_template_rules import check_template
from tests.conftest import new_password

BASE = "/api/v1/exam-templates"
AUTH = "/api/v1/auth"


async def _create_user(db, email: str, password: str, role: str) -> None:
    async with db() as s:
        uc = AuthUseCase(UserRepository(s), SessionRepository(s), get_password_service(), TokenService(), 168)
        await uc.create_user(email, password, role)


async def _login_as(client, db, email: str, role: str) -> None:
    password = new_password()
    await _create_user(db, email, password, role)
    client.cookies.clear()
    r = await client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


@pytest.fixture(autouse=True)
async def as_admin(client, db):
    await _login_as(client, db, "admin-templates@example.com", "admin")

GK1_11 = {
    "name": "Giữa kỳ 1 lớp 11 (mẫu thử)",
    "exam_type": "GK1",
    "grade": 11,
    "duration_minutes": 90,
    "sections": [
        {
            "order": 2,
            "title": "Phần II. Đúng sai",
            "question_type": "TRUE_FALSE",
            "count": 2,
            "chapter_codes": ["11C1"],
        },
        {
            "order": 1,
            "title": "Phần I. Trắc nghiệm",
            "question_type": "SINGLE_CHOICE",
            "count": 10,
            "points_per_question": 0.25,
            "difficulty_distribution": {"NB": 4, "TH": 4, "VD": 2},
            "chapter_codes": ["11C1", "11C2"],
        },
    ],
}

THPT = {
    "name": "Tốt nghiệp THPT (mẫu thử)",
    "exam_type": "THPT",
    "source": "Nguồn thử trong test",
    "sections": [{"order": 1, "title": "Phần I", "question_type": "SINGLE_CHOICE", "count": 12}],
}


def _with(base: dict, **changes) -> dict:
    data = copy.deepcopy(base)
    data.update(changes)
    return data


async def _create(client, body: dict) -> dict:
    r = await client.post(BASE, json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def _approve(client, template_id: int):
    return await client.post(f"{BASE}/{template_id}/approve")


async def test_create_is_draft_sorted_and_totalled(client):
    body = await _create(client, GK1_11)
    assert body["status"] == "DRAFT"
    assert body["approved_at"] is None
    assert body["total_questions"] == 12
    assert [s["order"] for s in body["sections"]] == [1, 2]

    got = await client.get(f"{BASE}/{body['template_id']}")
    assert got.status_code == 200
    assert got.json()["name"] == GK1_11["name"]


async def test_draft_hidden_from_lookup_until_approved(client):
    body = await _create(client, GK1_11)
    tid = body["template_id"]

    assert (await client.get(f"{BASE}/lookup", params={"exam_type": "GK1", "grade": 11})).json() == []

    # Thiếu nguồn: không được duyệt, vẫn là nháp.
    r = await _approve(client, tid)
    assert r.status_code == 422
    assert any("nguồn" in e for e in r.json()["detail"]["errors"])
    assert (await client.get(f"{BASE}/{tid}")).json()["status"] == "DRAFT"

    fixed = await client.put(f"{BASE}/{tid}", json=_with(GK1_11, source="Ma trận tổ Toán (thử)"))
    assert fixed.status_code == 200
    approved = await _approve(client, tid)
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approved_at"] is not None

    found = (await client.get(f"{BASE}/lookup", params={"exam_type": "GK1", "grade": 11})).json()
    assert [t["template_id"] for t in found] == [tid]


async def test_edit_of_approved_template_is_used_immediately(client):
    tid = (await _create(client, _with(GK1_11, source="nguồn thử")))["template_id"]
    await _approve(client, tid)

    new_sections = copy.deepcopy(GK1_11["sections"])
    new_sections[1]["count"] = 8
    new_sections[1]["difficulty_distribution"] = {"NB": 4, "TH": 2, "VD": 2}
    r = await client.put(f"{BASE}/{tid}", json=_with(GK1_11, source="nguồn thử", sections=new_sections))
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"

    found = (await client.get(f"{BASE}/lookup", params={"exam_type": "GK1", "grade": 11})).json()
    assert found[0]["total_questions"] == 10


async def test_invalid_edit_of_approved_template_is_rejected(client):
    tid = (await _create(client, _with(GK1_11, source="nguồn thử")))["template_id"]
    await _approve(client, tid)

    r = await client.put(f"{BASE}/{tid}", json=_with(GK1_11, source="  "))
    assert r.status_code == 422
    still = (await client.get(f"{BASE}/{tid}")).json()
    assert still["status"] == "APPROVED"
    assert still["source"] == "nguồn thử"


async def test_lookup_filters_by_type_and_grade(client):
    gk = (await _create(client, _with(GK1_11, source="s")))["template_id"]
    thpt = (await _create(client, THPT))["template_id"]
    await _approve(client, gk)
    await _approve(client, thpt)

    by_grade_10 = (await client.get(f"{BASE}/lookup", params={"exam_type": "GK1", "grade": 10})).json()
    assert by_grade_10 == []
    # Mẫu THPT không ghi khối vẫn khớp khi học sinh nói mình lớp 12.
    thpt_12 = (await client.get(f"{BASE}/lookup", params={"exam_type": "THPT", "grade": 12})).json()
    assert [t["template_id"] for t in thpt_12] == [thpt]
    assert (await client.get(f"{BASE}/lookup", params={"exam_type": "HSA"})).json() == []


async def test_admin_list_filters_by_status(client):
    draft = (await _create(client, GK1_11))["template_id"]
    approved = (await _create(client, THPT))["template_id"]
    await _approve(client, approved)

    drafts = (await client.get(BASE, params={"status": "DRAFT"})).json()
    assert [t["template_id"] for t in drafts] == [draft]
    assert len((await client.get(BASE)).json()) == 2


async def test_business_rule_errors_return_422(client):
    cases = [
        _with(GK1_11, grade=None),                      # giữa kỳ phải có khối
        _with(THPT, grade=11),                          # thi tốt nghiệp chỉ khối 12
    ]
    bad_dist = copy.deepcopy(GK1_11)
    bad_dist["sections"][1]["difficulty_distribution"] = {"NB": 1}
    cases.append(bad_dist)
    wrong_chapter = copy.deepcopy(GK1_11)
    wrong_chapter["sections"][0]["chapter_codes"] = ["12C1"]
    cases.append(wrong_chapter)
    dup_order = copy.deepcopy(GK1_11)
    dup_order["sections"][0]["order"] = 1
    cases.append(dup_order)

    for body in cases:
        r = await client.post(BASE, json=body)
        assert r.status_code == 422, body
        assert r.json()["detail"]["errors"]


async def test_shape_errors_and_404(client):
    assert (await client.post(BASE, json=_with(GK1_11, exam_type="XYZ"))).status_code == 422
    assert (await client.post(BASE, json=_with(GK1_11, sections=[]))).status_code == 422
    assert (await client.get(f"{BASE}/lookup")).status_code == 422      # thiếu exam_type
    assert (await client.get(f"{BASE}/999")).status_code == 404
    assert (await client.put(f"{BASE}/999", json=GK1_11)).status_code == 404
    assert (await _approve(client, 999)).status_code == 404


def test_rules_are_usable_without_http():
    data = ExamTemplateIn.model_validate(GK1_11)
    assert check_template(data, for_approval=False) == []
    assert len(check_template(data, for_approval=True)) == 1
    bad = ExamTemplateIn.model_validate(_with(GK1_11, grade=None))
    assert any("khối" in e for e in check_template(bad, for_approval=False))


# ---------- phân quyền (Auth #8) ----------

async def test_admin_routes_require_login_and_admin_role(client, db):
    tid = (await _create(client, _with(GK1_11, source="nguồn thử")))["template_id"]
    await _approve(client, tid)
    admin_calls = [
        ("post", BASE, GK1_11),
        ("get", BASE, None),
        ("get", f"{BASE}/{tid}", None),
        ("put", f"{BASE}/{tid}", GK1_11),
        ("post", f"{BASE}/{tid}/approve", None),
    ]

    client.cookies.clear()                                            # chưa đăng nhập: 401 ở mọi route
    for method, url, body in admin_calls:
        r = await client.request(method, url, json=body)
        assert r.status_code == 401, (method, url, r.text)
    assert (await client.get(f"{BASE}/lookup", params={"exam_type": "GK1"})).status_code == 401

    await _login_as(client, db, "hs-templates@example.com", "student")  # học sinh: 403 ở route quản trị
    for method, url, body in admin_calls:
        r = await client.request(method, url, json=body)
        assert r.status_code == 403, (method, url, r.text)
        assert r.json()["code"] == "FORBIDDEN_ROLE"                  # định dạng lỗi chung của auth (#8)
    found = await client.get(f"{BASE}/lookup", params={"exam_type": "GK1", "grade": 11})
    assert found.status_code == 200 and [t["template_id"] for t in found.json()] == [tid]


async def test_student_lookup_never_sees_drafts(client, db):
    await _create(client, GK1_11)                                     # admin tạo mẫu nháp
    await _login_as(client, db, "hs-drafts@example.com", "student")
    assert (await client.get(f"{BASE}/lookup", params={"exam_type": "GK1"})).json() == []
