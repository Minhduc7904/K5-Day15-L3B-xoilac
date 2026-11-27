from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Lớp gốc cho mọi model ORM. Alembic đọc Base.metadata."""
