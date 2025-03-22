async def stock_pipeline(**kwargs):
    """股票相關的 pipeline 邏輯"""
    source_type = kwargs.get("source_type")
    source = kwargs.get("source")
    limit = kwargs.get("limit", 150)
    
    # 實現股票相關的邏輯
    # ...

async def us_stock_pipeline(**kwargs):
    """美股相關的 pipeline 邏輯"""
    # ... 