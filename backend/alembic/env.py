import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Ensure root and backend directories are in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = root_dir / "backend"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

try:
    from app.config import settings
    from app.database.models import Base
except ImportError:
    from backend.app.config import settings
    from backend.app.database.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set model metadata
target_metadata = Base.metadata

# Inject database URL from settings or environment
db_url = os.getenv("DATABASE_URL") or getattr(settings, "DATABASE_URL", None)
if db_url:
    # Ensure asyncpg driver prefix for async engine
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations in 'online' mode with async connection."""
    # Ensure pgvector extension is present
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an Engine and associate a connection with the context."""
    connectable = create_async_engine(db_url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
