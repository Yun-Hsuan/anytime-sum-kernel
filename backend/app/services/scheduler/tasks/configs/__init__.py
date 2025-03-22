"""Task configurations"""
from app.services.scheduler.tasks.configs.news_summary_pipeline import get_news_summary_pipeline_configs
# 未來可以添加更多配置
# from .stock_pipeline import get_stock_pipeline_configs
# from .system_pipeline import get_system_pipeline_configs

def get_all_task_configs():
    """獲取所有任務配置"""
    configs = {}
    
    # 整合所有配置
    configs.update(get_news_pipeline_configs())
    # 未來添加更多配置
    # configs.update(get_stock_pipeline_configs())
    # configs.update(get_system_pipeline_configs())
    
    return configs 