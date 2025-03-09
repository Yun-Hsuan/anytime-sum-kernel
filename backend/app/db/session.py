from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable
from sqlalchemy import text
from sqlmodel import SQLModel
import logging

from app.core.config import settings
from app.models.article import RawArticle, ProcessedArticle, LatestSummary
from app.models.auth.models import User, Item

# Configure logging
logger = logging.getLogger(__name__)

# Define table mappings
TABLE_MAPPINGS = {
    'rawarticle': RawArticle.__table__,
    'processedarticle': ProcessedArticle.__table__,
    'latestsummary': LatestSummary.__table__,
    'user': User.__table__,
    'item': Item.__table__
}

# Create async engine
engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    echo=settings.ENVIRONMENT == "local" and settings.DEBUG_SQL,  # Only enable echo in local environment with DEBUG_SQL=True
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

# Dependency to get async session
async def get_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Initialize database
async def init_db(table_name: str = None):
    """
    Initialize the database:
    1. Import all models to ensure they are in the SQLModel metadata
    2. Create tables if they don't exist
    
    Args:
        table_name: Optional[str] - If specified, only create the specified table
                   Valid values: {', '.join(TABLE_MAPPINGS.keys())}
    
    Note: This will NOT update existing table structures
    For schema updates, use proper migration tools like Alembic
    """
    async with engine.begin() as conn:
        if table_name:
            # Validate table name
            if table_name.lower() not in TABLE_MAPPINGS:
                raise ValueError(f"Invalid table name. Must be one of: {', '.join(TABLE_MAPPINGS.keys())}")
            
            # Create specified table
            table = TABLE_MAPPINGS[table_name.lower()]
            await conn.run_sync(SQLModel.metadata.create_all, tables=[table])
            logger.info(f"Created table: {table_name}")
        else:
            # Create all tables
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Created all database tables")

# Cleanup database connections
async def close_db():
    """
    Clean up database connections
    """
    logger.info("Closing database connections")
    await engine.dispose() 