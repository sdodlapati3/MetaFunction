"""
Deepseek API client implementation.
"""

import logging
import requests
from typing import Optional

from .base_client import BaseAIClient
from app.utils.exceptions import APIError

logger = logging.getLogger(__name__)


class DeepSeekClient(BaseAIClient):
    """Deepseek API client with fallback endpoints."""
    
    def __init__(self):
        """Initialize Deepseek client."""
        super().__init__('DEEPSEEK_API_KEY')
        
        # Multiple endpoints to try for reliability
        self.endpoints = [
            "https://api.deepseek.ai/v1/chat/completions",
            "https://api.deepseek.com/v1/chat/completions"
        ]
        
        # Model mapping from friendly names to API model identifiers
        self.model_map = {
            "deepseek-chat": "deepseek-llm-7b-chat",
            "deepseek-coder": "deepseek-coder-7b-instruct"
        }
    
    def get_response(self, model: str, prompt: str) -> str:
        """
        Get response from Deepseek model.
        
        Args:
            model: Deepseek model identifier
            prompt: Input prompt
            
        Returns:
            Model response text
            
        Raises:
            APIError: If API call fails on all endpoints
        """
        if not self.is_available():
            return self.get_config_error_message()
        
        # Map friendly model name to actual API model identifier
        actual_model = self.model_map.get(model, "deepseek-llm-7b-chat")
        logger.info(f"Making request to Deepseek API with model: {actual_model}")
        
        # Try each endpoint until one succeeds
        for endpoint in self.endpoints:
            try:
                logger.info(f"Trying Deepseek endpoint: {endpoint}")
                
                response = requests.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": actual_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=15  # Shorter timeout to try multiple endpoints
                )
                
                logger.info(f"Deepseek API response status from {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"Deepseek API request successful on {endpoint}")
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Deepseek API error on {endpoint}: {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Connection to Deepseek endpoint {endpoint} failed: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error with Deepseek endpoint {endpoint}: {e}")
                continue
        
        # If all endpoints failed, raise an error
        error_msg = "All Deepseek endpoints failed"
        logger.error(error_msg)
        raise APIError(error_msg)
    
    def is_available(self) -> bool:
        """Check if Deepseek client is properly configured."""
        return bool(self.api_key)
