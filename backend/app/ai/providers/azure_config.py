from typing import Dict
from app.core.config import settings

class AzureOpenAISettings:
    """Azure OpenAI 服務配置"""
    
    # 部署名稱映射
    AZURE_OPENAI_DEPLOYMENTS: Dict[str, str] = {
        "gpt-4": "gpt-4o-mini"  # 目前只啟用了這個部署
    }
    
    @property
    def AZURE_OPENAI_ENDPOINT(self) -> str:
        return settings.AZURE_OPENAI_ENDPOINT
        
    @property
    def AZURE_OPENAI_API_KEY(self) -> str:
        return settings.AZURE_OPENAI_API_KEY
        
    @property
    def AZURE_OPENAI_API_VERSION(self) -> str:
        return settings.AZURE_OPENAI_API_VERSION 