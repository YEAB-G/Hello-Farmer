"""Database initialization script."""
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database.models import Base


async def init_db():
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1]}")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        print("Creating extensions and schema tables...")
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Database schema successfully initialized!")


if __name__ == "__main__":
    asyncio.run(init_db())
