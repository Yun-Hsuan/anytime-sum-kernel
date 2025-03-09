import asyncio
import logging
from sqlalchemy import inspect, text
from app.db.session import engine, init_db

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 預期的表名列表
EXPECTED_TABLES = {
    # 用戶認證相關表
    'user',
    'item',
    
    # 文章相關表
    'rawarticle',
    'processedarticle',
}

async def test_database_connection():
    """測試數據庫連接"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text('SELECT 1'))
            assert result.scalar() == 1
            logger.info("數據庫連接測試成功")
    except Exception as e:
        logger.error(f"數據庫連接測試失敗: {str(e)}")
        raise

async def test_create_tables():
    """測試創建所有表"""
    try:
        await init_db()
        logger.info("數據庫表創建完成")
    except Exception as e:
        logger.error(f"創建表失敗: {str(e)}")
        raise

async def test_verify_tables():
    """驗證所有預期的表是否存在"""
    try:
        inspector = inspect(engine)
        actual_tables = set(await inspector.get_table_names())
        
        # 檢查是否所有預期的表都存在
        missing_tables = EXPECTED_TABLES - actual_tables
        if missing_tables:
            logger.error(f"缺少以下表: {missing_tables}")
            raise Exception(f"缺少必要的表: {missing_tables}")
        
        # 記錄所有找到的表
        logger.info("找到以下表:")
        for table in sorted(actual_tables):
            if table in EXPECTED_TABLES:
                logger.info(f"✓ {table}")
            else:
                logger.info(f"- {table} (額外表)")
                
        logger.info("表驗證完成")
    except Exception as e:
        logger.error(f"表驗證失敗: {str(e)}")
        raise

async def main():
    """主測試函數"""
    try:
        logger.info("開始數據庫初始化測試")
        
        # 測試數據庫連接
        await test_database_connection()
        
        # 測試創建表
        await test_create_tables()
        
        # 驗證表的存在
        await test_verify_tables()
        
        logger.info("所有測試完成")
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {str(e)}")
        raise
    finally:
        # 清理連接
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main()) 