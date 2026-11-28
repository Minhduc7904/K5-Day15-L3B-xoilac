"""Allow the CANCELLED preview status that the live exam chat already writes."""
from alembic import op

revision = "0017_preview_cancelled"
down_revision = "0016_notifications"
branch_labels = None
depends_on = None

NAME = "ck_exam_previews_status"
TABLE = "exam_previews"


def upgrade() -> None:
    op.drop_constraint(NAME, TABLE, type_="check")
    op.create_check_constraint(NAME, TABLE, "status IN ('PROPOSED','EDITED','CONFIRMED','BUILT','CANCELLED')")


def downgrade() -> None:
    op.execute(f"UPDATE {TABLE} SET status = 'EDITED' WHERE status = 'CANCELLED'")
    op.drop_constraint(NAME, TABLE, type_="check")
    op.create_check_constraint(NAME, TABLE, "status IN ('PROPOSED','EDITED','CONFIRMED','BUILT')")
