from typing import Optional, Dict, Any
import logging
import requests
from .azure_config import AzureOpenAISettings

logger = logging.getLogger(__name__)

class AzureOpenAIClient:
    """Azure OpenAI 客戶端管理器"""
    
    def __init__(self):
        self.settings = AzureOpenAISettings()
        # 設置 API 端點和密鑰
        self.api_endpoint = self.settings.AZURE_OPENAI_ENDPOINT
        self.api_key = self.settings.AZURE_OPENAI_API_KEY
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
    async def get_completion(
        self,
        messages: list,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = 8000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        獲取 AI 完成結果
        
        Args:
            messages: 對話消息列表
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 其他參數
            
        Returns:
            Dict[str, Any]: API 響應結果
        """
        try:
            # 構建完整的 API URL
            deployment = self.settings.AZURE_OPENAI_DEPLOYMENTS.get(model, model)
            api_url = f"{self.api_endpoint}/openai/deployments/{deployment}/chat/completions?api-version={self.settings.AZURE_OPENAI_API_VERSION}"
            
            # 準備請求數據
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            # 發送請求
            response = requests.post(
                api_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Azure OpenAI API 調用失敗: {str(e)}")
            raise
            
    async def get_embedding(
        self,
        text: str,
        model: str = "text-embedding-ada-002"
    ) -> list:
        """
        獲取文本嵌入向量
        
        Args:
            text: 輸入文本
            model: 模型名稱
            
        Returns:
            list: 嵌入向量
        """
        try:
            # 構建完整的 API URL
            deployment = self.settings.AZURE_OPENAI_DEPLOYMENTS.get(model, model)
            api_url = f"{self.api_endpoint}/openai/deployments/{deployment}/embeddings?api-version={self.settings.AZURE_OPENAI_API_VERSION}"
            
            # 準備請求數據
            payload = {
                "input": text
            }
            
            # 發送請求
            response = requests.post(
                api_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result["data"][0]["embedding"]
            
        except Exception as e:
            logger.error(f"Azure OpenAI Embedding API 調用失敗: {str(e)}")
            raise 