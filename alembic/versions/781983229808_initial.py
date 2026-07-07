"""initial

Revision ID: 781983229808
Revises:
Create Date: 2026-04-11 21:20:47.107287

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "781983229808"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("email", sa.VARCHAR(length=255), nullable=False),
        sa.Column("password_hash", sa.VARCHAR(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "token_blacklist",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("jti", sa.VARCHAR(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_token_blacklist_jti"), "token_blacklist", ["jti"], unique=True
    )
    op.create_index(
        op.f("ix_token_blacklist_expires_at"),
        "token_blacklist",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "habits",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=255), nullable=False),
        sa.Column("description", sa.VARCHAR(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name=op.f("uq_user_habit_name")),
    )
    op.create_index(op.f("idx_habit_user_id"), "habits", ["user_id"], unique=False)

    op.create_table(
        "habit_logs",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("habit_id", sa.INTEGER(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("date", sa.DATE(), nullable=False),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("habit_id", "date", name=op.f("uq_habit_log_date")),
    )
    op.create_index(
        op.f("idx_habit_log_habit_date"),
        "habit_logs",
        ["habit_id", "date"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_table("habit_logs")
    op.drop_index(op.f("idx_habit_user_id"), table_name="habits")
    op.drop_table("habits")
    op.drop_index(op.f("ix_token_blacklist_expires_at"), table_name="token_blacklist")
    op.drop_index(op.f("ix_token_blacklist_jti"), table_name="token_blacklist")
    op.drop_table("token_blacklist")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    # ### end Alembic commands ###
