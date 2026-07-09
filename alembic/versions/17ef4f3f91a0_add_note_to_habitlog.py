"""add note to habitlog

Revision ID: 17ef4f3f91a0
Revises: 241bdfb8967e
Create Date: 2026-07-09 22:30:41.108342

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "17ef4f3f91a0"
down_revision: Union[str, Sequence[str], None] = "241bdfb8967e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "habit_logs",
        sa.Column("note", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("habit_logs", "note")
