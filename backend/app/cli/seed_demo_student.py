"""Tạo dữ liệu demo cho tài khoản học sinh từ mật khẩu nhận qua stdin."""

import argparse
import asyncio
import sys

from app.cli.common import default_session, utf8_console, validate_email
from app.models.user import ROLE_STUDENT, STATUS_ACTIVE
from app.repositories.student_profiles import StudentProfileRepository
from app.repositories.user_repository import DuplicateEmailError, UserRepository
from app.schemas.student import ProfileIn
from app.service.password_service import PasswordService
from app.usecase.auth import PASSWORD_MAX


async def seed(email: str, password: str) -> str:
    passwords = PasswordService()
    profile = ProfileIn(
        school_name="Trường THPT Demo",
        grade=12,
        target_score=8,
        exam_period="final_1",
        study_days=[1, 3, 5],
        display_name="Học sinh Demo",
    )
    async with default_session() as session:
        users = UserRepository(session)
        profiles = StudentProfileRepository(session)
        existing = await users.get_by_email(email)
        if existing is None:
            try:
                user = await users.add(
                    email,
                    await passwords.hash(password),
                    ROLE_STUDENT,
                    profile.display_name,
                    commit=False,
                )
            except DuplicateEmailError:
                return "Email vừa được đăng ký. Kiểm tra trước khi chạy lại."

            values = profile.model_dump(exclude={"study_days", "display_name"})
            await profiles.save(user, values, profile.study_days, profile.display_name)
            return ""

        if (
            existing.role != ROLE_STUDENT
            or existing.status != STATUS_ACTIVE
            or existing.password_hash is None
            or not await passwords.verify(existing.password_hash, password)
            or await profiles.get(existing.user_id) is None
        ):
            return "Email đã được sử dụng. Chọn địa chỉ khác hoặc kiểm tra tài khoản đã có."
        return ""


def main() -> int:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="Email dành riêng cho tài khoản demo")
    args = parser.parse_args()
    email = validate_email(args.email)
    password = sys.stdin.readline().rstrip("\r\n")
    if not email or not 12 <= len(password) <= PASSWORD_MAX:
        parser.error(f"Cần email hợp lệ và mật khẩu dài 12–{PASSWORD_MAX} ký tự qua stdin.")

    error = asyncio.run(seed(email, password))
    if error:
        print(error, file=sys.stderr)
        return 1
    print(f"Tài khoản học sinh demo sẵn sàng: {email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
