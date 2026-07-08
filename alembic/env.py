from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.db.models.user import User  # noqa: F401
from app.db.models.grupo import Grupo  # noqa: F401
from app.db.models.tarea import Tarea  # noqa: F401
from app.db.models.alumno import Alumno  # noqa: F401
from app.db.models.entrega import Entrega  # noqa: F401
from app.db.models.revision import Revision  # noqa: F401
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

from app.core.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
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
