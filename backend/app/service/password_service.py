from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from starlette.concurrency import run_in_threadpool


class PasswordService:
    """Băm và kiểm mật khẩu bằng argon2id. Băm tốn CPU nên chạy trong threadpool.

    Không bao giờ log mật khẩu hay hash.
    """

    def __init__(self) -> None:
        self._hasher = PasswordHasher(type=Type.ID)
        # Hash giả để vẫn chạy verify khi email không tồn tại (thời gian phản hồi không lộ email).
        self._dummy_hash = self._hasher.hash("examind-dummy-password")

    def hash_sync(self, password: str) -> str:
        return self._hasher.hash(password)

    async def hash(self, password: str) -> str:
        return await run_in_threadpool(self._hasher.hash, password)

    async def verify(self, password_hash: str, password: str) -> bool:
        def _verify() -> bool:
            try:
                return self._hasher.verify(password_hash, password)
            except (VerificationError, InvalidHashError):
                return False

        return await run_in_threadpool(_verify)

    async def verify_dummy(self, password: str) -> None:
        """Tốn cùng thời gian như verify thật, luôn coi là sai."""
        await self.verify(self._dummy_hash, password)
