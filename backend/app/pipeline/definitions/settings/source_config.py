from pydantic_settings import BaseSettings

class SourceConfig(BaseSettings):
    DEFAULT_LIMIT: int = 150
    SUMMARY_LIMIT: int = 30
    SOURCE_TYPES: list[str] = ["tw_stock", "us_stock", "hot_news"]
    
    class Config:
        env_prefix = "PIPELINE_SOURCE_" 