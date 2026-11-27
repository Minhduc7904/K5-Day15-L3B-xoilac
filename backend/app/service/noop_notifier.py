from app.usecase.ports import RevokeReason


class NoopRealtimeNotifier:
    """RealtimeNotifier không làm gì. Dùng cho CLI và cho chỗ không có kết nối socket nào để ngắt."""

    async def kick_user(self, user_id: int, reason: RevokeReason) -> None:
        return None

    async def kick_session(self, session_id: int, reason: RevokeReason) -> None:
        return None
