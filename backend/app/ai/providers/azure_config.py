from typing import Dict
from app.core.config import settings

class AzureOpenAISettings:
    """Azure OpenAI Service Configuration"""
    
    # Deployment name mapping
    AZURE_OPENAI_DEPLOYMENTS: Dict[str, str] = {
        "gpt-4": "gpt-4o-mini"  # Only this deployment is currently enabled
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
    
    @property
    def AZURE_OPENAI_DEPLOYMENT_NAME(self) -> str:
        return settings.AZURE_OPENAI_DEPLOYMENT_NAME