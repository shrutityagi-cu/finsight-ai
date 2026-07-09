from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy import engine_from_config


from app.config.settings import settings
from app.database.base import Base

# Import every model so SQLAlchemy registers them before Alembic autogenerate.
import app.models  # noqa: F401

config = context.config
# Alembic's ini parsing uses configparser interpolation. Escape '%' in URLs.
_db_url_raw = str(settings.database_url).strip()
# If settings.database_url accidentally includes the literal prefix
# 'DATABASE_URL=' (env_file parsing), strip it out.
if _db_url_raw.upper().startswith("DATABASE_URL="):
    _db_url_raw = _db_url_raw.split("=", 1)[1]

_db_url_raw = _db_url_raw.strip()


_db_url_sync = _db_url_raw.replace("postgresql+asyncpg://", "postgresql://", 1)
_db_url_sync = _db_url_sync.replace("%", "%%")
config.set_main_option("sqlalchemy.url", _db_url_sync)






if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=_db_url_sync,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)




if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

