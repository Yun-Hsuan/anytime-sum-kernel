import logging
from pydantic_settings import BaseSettings

class LogConfig(BaseSettings):
    """日誌配置管理"""
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "pipeline.log"
    
    def get_logger(self, name: str) -> logging.Logger:
        """獲取配置好的 logger"""
        logger = logging.getLogger(f"pipeline.{name}")
        
        if not logger.handlers:
            # 檔案處理器
            handler = logging.FileHandler(self.LOG_FILE)
            formatter = logging.Formatter(self.LOG_FORMAT)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # 控制台處理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            logger.setLevel(getattr(logging, self.LOG_LEVEL))
        
        return logger
    
    class Config:
        env_prefix = "PIPELINE_LOG_" 