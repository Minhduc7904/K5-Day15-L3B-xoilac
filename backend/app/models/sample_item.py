from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SampleItem(Base):
    """Bảng mẫu để chứng minh ghi/đọc qua ORM. Không phải schema nghiệp vụ."""

    __tablename__ = "sample_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
