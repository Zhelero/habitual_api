"""align db schema with models: timezone-aware timestamps, shorten habits.name

Revision ID: 241bdfb8967e
Revises: da5c13968d93
Create Date: 2026-07-03 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "241bdfb8967e"
down_revision: Union[str, Sequence[str], None] = "da5c13968d93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Existing TIMESTAMP columns hold naive datetimes that were always written
# as UTC by the application (datetime.now(timezone.utc)), just silently
# stripped of tzinfo on the way in. Reinterpreting them as UTC on the way
# to TIMESTAMPTZ is a no-op for the actual instant in time — it just makes
# that assumption explicit and enforced going forward.
_TIMESTAMP_COLUMNS = [
    ("users", "created_at"),
    ("users", "updated_at"),
    ("habits", "created_at"),
    ("habits", "updated_at"),
    ("habit_logs", "created_at"),
    ("token_blacklist", "expires_at"),
    ("token_blacklist", "created_at"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for table, column in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    op.alter_column(
        "habits",
        "name",
        existing_type=sa.String(length=255),
        type_=sa.String(length=100),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "habits",
        "name",
        existing_type=sa.String(length=100),
        type_=sa.String(length=255),
        existing_nullable=False,
    )

    for table, column in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.TIMESTAMP(),
            existing_nullable=False,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
