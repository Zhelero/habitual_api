from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context

from app.core.config import settings
from app.db.base import Base

# Models must be imported so they register themselves on Base.metadata.
# Base itself has no knowledge of them until this import runs — without it,
# target_metadata below is empty whenever alembic is invoked standalone
# (e.g. `alembic check` in CI), and Alembic thinks every existing table
# should be dropped.
import app.db.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return settings.DATABASE_URL


def run_migrations_offline():
    url = get_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(
        get_url(),
        pool_pre_ping=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
