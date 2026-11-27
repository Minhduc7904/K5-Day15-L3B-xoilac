"""Bảng đầy đủ luật phân quyền quản lý người dùng (#20): hàm thuần can_manage, không cần DB.

Actor: admin gốc (ROOT), admin thường (ADMIN). Target: admin gốc, admin khác, học sinh, chính mình.
Action: create, update (display_name / email / role / status), reset_password.
"""
import pytest

from app.usecase.auth import RoleForbidden
from app.usecase.user_management import CannotModifyRoot, CannotModifySelf, Principal, can_manage

ROOT = Principal(user_id=1, role="admin", is_root=True)
ADMIN = Principal(user_id=2, role="admin", is_root=False)
OTHER_ADMIN = Principal(user_id=3, role="admin", is_root=False)
STUDENT = Principal(user_id=4, role="student", is_root=False)

OK = None
FORBIDDEN = RoleForbidden
NO_ROOT = CannotModifyRoot
NO_SELF = CannotModifySelf

NAME = ("update", {"display_name": "Tên mới"})
EMAIL = ("update", {"email": "moi@example.com"})
TO_STUDENT = ("update", {"role": "student"})
TO_ADMIN = ("update", {"role": "admin"})
DISABLE = ("update", {"status": "disabled"})
ENABLE = ("update", {"status": "active"})
RESET = ("reset_password", {})

CASES = [
    # ---- Tạo tài khoản ----
    (ROOT, None, ("create", {"role": "student"}), OK),
    (ROOT, None, ("create", {"role": "admin"}), OK),
    (ADMIN, None, ("create", {"role": "student"}), OK),
    (ADMIN, None, ("create", {"role": "admin"}), FORBIDDEN),
    # ---- Admin gốc thao tác với chính mình: chỉ sửa display_name ----
    (ROOT, ROOT, NAME, OK),
    (ROOT, ROOT, EMAIL, NO_ROOT),
    (ROOT, ROOT, TO_STUDENT, NO_ROOT),
    (ROOT, ROOT, DISABLE, NO_ROOT),
    (ROOT, ROOT, ENABLE, NO_ROOT),
    (ROOT, ROOT, RESET, NO_ROOT),
    # ---- Admin gốc thao tác với admin khác: được hết ----
    (ROOT, OTHER_ADMIN, NAME, OK),
    (ROOT, OTHER_ADMIN, EMAIL, OK),
    (ROOT, OTHER_ADMIN, TO_STUDENT, OK),
    (ROOT, OTHER_ADMIN, DISABLE, OK),
    (ROOT, OTHER_ADMIN, ENABLE, OK),
    (ROOT, OTHER_ADMIN, RESET, OK),
    # ---- Admin gốc thao tác với học sinh: được hết, kể cả nâng thành admin ----
    (ROOT, STUDENT, NAME, OK),
    (ROOT, STUDENT, EMAIL, OK),
    (ROOT, STUDENT, TO_ADMIN, OK),
    (ROOT, STUDENT, DISABLE, OK),
    (ROOT, STUDENT, RESET, OK),
    # ---- Admin thường thao tác với admin gốc ----
    (ADMIN, ROOT, NAME, FORBIDDEN),
    (ADMIN, ROOT, EMAIL, NO_ROOT),
    (ADMIN, ROOT, TO_STUDENT, NO_ROOT),
    (ADMIN, ROOT, DISABLE, NO_ROOT),
    (ADMIN, ROOT, RESET, NO_ROOT),
    # ---- Admin thường thao tác với admin khác: xem được (không qua hàm này), sửa thì không ----
    (ADMIN, OTHER_ADMIN, NAME, FORBIDDEN),
    (ADMIN, OTHER_ADMIN, EMAIL, FORBIDDEN),
    (ADMIN, OTHER_ADMIN, TO_STUDENT, FORBIDDEN),
    (ADMIN, OTHER_ADMIN, DISABLE, FORBIDDEN),
    (ADMIN, OTHER_ADMIN, ENABLE, FORBIDDEN),
    (ADMIN, OTHER_ADMIN, RESET, FORBIDDEN),
    # ---- Admin thường thao tác với chính mình ----
    (ADMIN, ADMIN, DISABLE, NO_SELF),
    (ADMIN, ADMIN, TO_STUDENT, NO_SELF),
    (ADMIN, ADMIN, NAME, FORBIDDEN),  # tài khoản admin: chỉ admin gốc quản lý
    (ADMIN, ADMIN, EMAIL, FORBIDDEN),
    (ADMIN, ADMIN, ENABLE, FORBIDDEN),
    (ADMIN, ADMIN, RESET, FORBIDDEN),
    # ---- Admin thường thao tác với học sinh ----
    (ADMIN, STUDENT, NAME, OK),
    (ADMIN, STUDENT, EMAIL, OK),
    (ADMIN, STUDENT, DISABLE, OK),
    (ADMIN, STUDENT, ENABLE, OK),
    (ADMIN, STUDENT, RESET, OK),
    (ADMIN, STUDENT, ("update", {"role": "student"}), OK),
    (ADMIN, STUDENT, TO_ADMIN, FORBIDDEN),  # không nâng học sinh thành admin
    (ADMIN, STUDENT, ("update", {"display_name": "X", "role": "admin"}), FORBIDDEN),
    # ---- Không ai đặt is_root qua API ----
    (ROOT, OTHER_ADMIN, ("update", {"is_root": True}), NO_ROOT),
    (ADMIN, STUDENT, ("update", {"is_root": True}), NO_ROOT),
    (ROOT, None, ("create", {"role": "admin", "is_root": True}), NO_ROOT),
]


def _id(case) -> str:
    names = {ROOT: "root", ADMIN: "admin", OTHER_ADMIN: "other_admin", STUDENT: "student", None: "none"}
    actor, target, (action, changes), expected = case
    target_name = "self" if target is actor else names[target]
    return f"{names[actor]}-{target_name}-{action}-{'+'.join(changes) or 'none'}-{getattr(expected, 'code', 'OK')}"


@pytest.mark.parametrize("case", CASES, ids=[_id(c) for c in CASES])
def test_can_manage(case):
    actor, target, (action, changes), expected = case
    assert can_manage(actor, target, action, changes) is expected
