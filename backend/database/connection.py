import os
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

BACKEND_DIR = Path(__file__).parent.parent
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{BACKEND_DIR}/bye_buy.db",
)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode for concurrent access from multiple services."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database with schema."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    schema_path = Path(__file__).parent / "schema.sql"
    if schema_path.exists():
        async with engine.begin() as conn:
            schema_sql = schema_path.read_text()
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(text(statement))


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
