"""add color to habits

Revision ID: da5c13968d93
Revises: 35274e78c30d
Create Date: 2026-06-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "da5c13968d93"
down_revision: Union[str, Sequence[str], None] = "35274e78c30d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "habits",
        sa.Column("color", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("habits", "color")
    # ### end Alembic commands ###
