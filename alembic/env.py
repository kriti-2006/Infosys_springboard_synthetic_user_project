import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from db.models import Base
from db.session import normalize_url

target_metadata = Base.metadata
URL = normalize_url(settings.DATABASE_URL)


def _run(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _online():
    engine = create_async_engine(URL)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_online())
