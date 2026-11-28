from typing import Literal, Protocol

# Lý do gửi kèm sự kiện "session:revoked" (payload {"reason": ...}, #20) để frontend báo đúng thông báo.
RevokeReason = Literal["logout", "disabled", "password_reset", "role_changed", "expired"]


class RealtimeNotifier(Protocol):
    async def revoke_session(self, session_id: int, reason: RevokeReason | None = None) -> None: ...

    async def revoke_user(self, user_id: int, reason: RevokeReason | None = None) -> None: ...
