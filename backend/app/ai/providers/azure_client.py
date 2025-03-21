from typing import Optional, Dict, Any
import logging
import requests
from .azure_config import AzureOpenAISettings

logger = logging.getLogger(__name__)

class AzureOpenAIClient:
    """Azure OpenAI Client Manager"""
    
    def __init__(self):
        self.settings = AzureOpenAISettings()
        # Set API endpoint and key
        self.api_endpoint = self.settings.AZURE_OPENAI_ENDPOINT
        self.api_key = self.settings.AZURE_OPENAI_API_KEY
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        self.deployment_name = self.settings.AZURE_OPENAI_DEPLOYMENT_NAME
        
    async def get_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 8000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get AI completion result
        
        Args:
            messages: List of conversation messages
            model: Model name
            temperature: Temperature parameter
            max_tokens: Maximum number of tokens
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: API response result
        """
        try:
            # Build complete API URL
            deployment = self.deployment_name
            api_url = f"{self.api_endpoint}/openai/deployments/{deployment}/chat/completions?api-version={self.settings.AZURE_OPENAI_API_VERSION}"
            
            # Prepare request data
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            # Send request
            response = requests.post(
                api_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Azure OpenAI API call failed: {str(e)}")
            raise
            
    async def get_embedding(
        self,
        text: str,
        model: str = "text-embedding-ada-002"
    ) -> list:
        """
        Get text embedding vector
        
        Args:
            text: Input text
            model: Model name
            
        Returns:
            list: Embedding vector
        """
        try:
            # Build complete API URL
            deployment = self.settings.AZURE_OPENAI_DEPLOYMENTS.get(model, model)
            api_url = f"{self.api_endpoint}/openai/deployments/{deployment}/embeddings?api-version={self.settings.AZURE_OPENAI_API_VERSION}"
            
            # Prepare request data
            payload = {
                "input": text
            }
            
            # Send request
            response = requests.post(
                api_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result["data"][0]["embedding"]
            
        except Exception as e:
            logger.error(f"Azure OpenAI Embedding API call failed: {str(e)}")
            raise 