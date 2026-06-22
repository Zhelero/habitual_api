"""add is_archived to habits

Revision ID: 35274e78c30d
Revises: 781983229808
Create Date: 2026-06-20 13:21:53.119055

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "35274e78c30d"
down_revision: Union[str, Sequence[str], None] = "781983229808"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "habits",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("habits", "is_archived")
    # ### end Alembic commands ###
