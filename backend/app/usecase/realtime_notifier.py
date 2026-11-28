from typing import Protocol


class RealtimeNotifier(Protocol):
    async def revoke_session(self, session_id: int) -> None: ...

    async def revoke_user(self, user_id: int) -> None: ...
