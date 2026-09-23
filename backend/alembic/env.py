import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from app.db import Base
from app import models  # noqa: F401
from app.config import settings

config=context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
if config.config_file_name: fileConfig(config.config_file_name)
target_metadata=Base.metadata

def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle":"named"})
    with context.begin_transaction(): context.run_migrations()

def do_run_migrations(connection):
    # Alembic 1.18 creates alembic_version.version_num as VARCHAR(32). Revision
    # ids such as 0025_v44_5_8_entitlement_idempotency do not fit, so a fresh
    # install stops there. Create the table at VARCHAR(128) first. An older
    # database is widened in the same transaction.
    # Backend and worker both run `alembic upgrade head` at boot. PostgreSQL
    # CREATE TABLE IF NOT EXISTS is not race-safe: the loser dies on
    # pg_type_typname_nsp_index and the API container exits before /health.
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        connection.exec_driver_sql("SELECT pg_advisory_xact_lock(872663041314)")
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(128) NOT NULL PRIMARY KEY)"
        )
        connection.exec_driver_sql("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)")
        context.run_migrations()

async def run_async():
    connectable=async_engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=None)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online(): asyncio.run(run_async())

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
