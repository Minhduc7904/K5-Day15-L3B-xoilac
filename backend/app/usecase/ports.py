"""Cổng (port) usecase dùng để báo ra ngoài mà không biết cách cài đặt (issue #20).

Usecase chỉ gọi qua Protocol này; bản cài đặt bằng python-socketio nằm ở app/service/socketio_notifier.py,
được ghép ở app/api/deps.py. Usecase không import socketio.
"""
from typing import Literal, Protocol

# Lý do gửi kèm sự kiện "session:revoked" để frontend hiển thị đúng thông báo.
RevokeReason = Literal["logout", "disabled", "password_reset", "role_changed", "expired"]


class RealtimeNotifier(Protocol):
    async def kick_user(self, user_id: int, reason: RevokeReason) -> None:
        """Gửi session:revoked tới MỌI kết nối của người dùng rồi ngắt chúng (khoá, đặt lại mật khẩu, hạ vai trò)."""
        ...

    async def kick_session(self, session_id: int, reason: RevokeReason) -> None:
        """Gửi session:revoked tới các kết nối mở bằng ticket của MỘT phiên rồi ngắt chúng (đăng xuất)."""
        ...
