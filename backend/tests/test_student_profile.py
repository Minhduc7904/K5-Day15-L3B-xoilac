import pytest

from app.service.google_identity import GoogleIdentity
from tests.test_auth import API, login, make_admin, register
from tests.test_student_auth import exchange, google_ticket

PROFILE = f"{API}/student/me/profile"
CREDITS = f"{API}/student/me/credits"
DETAILS = {
    "school_name": " Trường THPT Mẫu ",
    "grade": 12,
    "target_score": 9,
    "exam_period": "national_high_school",
    "study_days": [6, 1],
    "reminder_time": "08:00",
}


async def test_verified_student_completes_and_edits_profile(client):
    assert (await client.get(PROFILE)).status_code == 401
    await register(client, "hs01@example.com")
    assert (await client.get(PROFILE)).json() == {
        "completed": False, "profile": None, "email_verified": True,
    }
    response = await client.put(PROFILE, json={**DETAILS, "display_name": "Học sinh"})
    assert response.status_code == 200, response.text
    profile = response.json()
    assert profile["school_name"] == "Trường THPT Mẫu"
    assert profile["exam_period"] == "national_high_school"
    assert profile["study_days"] == [1, 6]
    assert profile["reminder_time"] == "08:00:00"
    assert profile["display_name"] == "Học sinh"

    await client.post(f"{API}/auth/logout")
    assert (await login(client)).status_code == 200
    assert (await client.get(PROFILE)).json()["profile"] == profile

    changed = await client.put(PROFILE, json={**DETAILS, "study_days": [3], "reminder_time": None})
    assert changed.json()["study_days"] == [3]
    assert (await client.get(PROFILE)).json()["profile"]["reminder_time"] is None
    credits = (await client.get(CREDITS)).json()
    assert credits["balance"] == credits["limit"] == 500
    assert credits["daily_grant"] == 100
    assert [entry["delta"] for entry in credits["history"]] == [500]
    assert credits["next_before_id"] is None


@pytest.mark.parametrize(("field", "value"), [
    ("school_name", "  "), ("grade", 9), ("target_score", 10), ("exam_period", "unknown"),
    ("study_days", []), ("study_days", [1, 1]), ("study_days", [7]), ("reminder_time", "08:00Z"),
])
async def test_profile_rejects_invalid_inputs(client, field, value):
    await register(client)
    assert (await client.put(PROFILE, json={**DETAILS, field: value})).status_code == 422
    assert not (await client.get(PROFILE)).json()["completed"]


async def test_admin_cannot_access_student_endpoints(client, db):
    await make_admin(db)
    assert (await login(client, "admin@example.com")).status_code == 200
    assert (await client.get(PROFILE)).status_code == 403
    assert (await client.get(CREDITS)).status_code == 403


async def test_google_registers_wallet_once(client):
    identity = GoogleIdentity("profile-google", "profile@gmail.com", "Học sinh", True)
    for _ in range(2):
        assert (await exchange(client, *await google_ticket(client, identity))).status_code == 200
        assert not (await client.get(PROFILE)).json()["completed"]
        credits = (await client.get(CREDITS)).json()
        assert [entry["reason"] for entry in credits["history"]] == ["initial_grant"]
