from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))

_candidates = [
    os.path.join(_HERE, "..", "api"),   # local layout
    os.path.join(_HERE, ".."),          # Docker layout (api/ contents flattened into /app)
]
for _path in _candidates:
    if os.path.isdir(os.path.join(_path, "models")):
        sys.path.insert(0, _path)
        break

from models.review import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

try:
    from core.config import get_settings
    _db_url = get_settings().database_url
    _sync_url = _db_url.replace("+asyncpg", "")
    config.set_main_option("sqlalchemy.url", _sync_url)
except Exception:
    pass

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()