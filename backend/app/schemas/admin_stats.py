from datetime import datetime

from pydantic import BaseModel, field_serializer


class OnlineStudentOut(BaseModel):
    user_id: int
    display_name: str | None
    email: str
    connections: int


class OnlineStatsOut(BaseModel):
    """`users`, `page`, `page_size` chỉ có khi gọi với ?include=users."""

    online_students: int
    connections: int
    as_of: datetime
    users: list[OnlineStudentOut] | None = None
    page: int | None = None
    page_size: int | None = None

    @field_serializer("as_of")
    def _iso_utc(self, value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")
