from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path

from ..config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database with schema."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Also run raw SQL schema for any additional setup
    schema_path = Path(__file__).parent / "schema.sql"
    if schema_path.exists():
        async with engine.begin() as conn:
            schema_sql = schema_path.read_text()
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(statement)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
