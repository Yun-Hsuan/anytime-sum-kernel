from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine, init_db, TABLE_MAPPINGS

router = APIRouter(prefix="/dev", tags=["development"])

@router.post("/drop-table/{table_name}")
async def drop_table(table_name: str):
    """
    Drop a specific database table
    Only available in development environment
    
    Args:
        table_name: Name of the table to drop
    """
    if settings.ENVIRONMENT != "local":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available in local development environment"
        )
    
    if table_name.lower() not in TABLE_MAPPINGS:
        raise HTTPException(
            status_code=400,
            detail=f"Table name must be one of: {', '.join(TABLE_MAPPINGS.keys())}"
        )
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            print(f"Dropped table {table_name}")
            
        return {"message": f"Database table {table_name} dropped successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to drop table {table_name}: {str(e)}"
        )

@router.post("/create-tables/{table_name}")
async def create_tables(table_name: str = None):
    """
    Create database tables
    Only available in development environment
    
    Args:
        table_name: Optional - Name of the table to create (e.g., 'rawarticle' or 'processedarticle').
                   If not specified, creates all tables.
    """
    if settings.ENVIRONMENT != "local":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available in local development environment"
        )
    
    try:
        await init_db(table_name)
        if table_name:
            return {"message": f"Database table {table_name} created successfully"}
        else:
            return {"message": "All database tables created successfully"}
    except Exception as e:
        if table_name:
            detail = f"Failed to create table {table_name}: {str(e)}"
        else:
            detail = f"Failed to create tables: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)