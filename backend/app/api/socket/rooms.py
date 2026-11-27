"""Nơi DUY NHẤT sinh tên room Socket.IO (#20). Không viết chuỗi tên room ở chỗ khác."""
from app.usecase.realtime import RoomKey


def role_room(role: str) -> str:
    return f"role:{role}"


def user_room(user_id: int) -> str:
    return f"user:{user_id}"


def room_name(key: RoomKey) -> str:
    kind, value = key
    if kind == "role":
        return role_room(str(value))
    if kind == "user":
        return user_room(int(value))
    raise ValueError(f"Loại room không hợp lệ: {kind}")
