"""
Perplexity API client implementation.
"""

import logging
import requests
from typing import Optional

from .base_client import BaseAIClient
from app.utils.exceptions import APIError

logger = logging.getLogger(__name__)


class PerplexityClient(BaseAIClient):
    """Perplexity API client."""
    
    def __init__(self):
        """Initialize Perplexity client."""
        super().__init__('PERPLEXITY_API_KEY')
        
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        
        # Model mapping from friendly names to API model identifiers
        self.model_map = {
            "perplexity-online-llama3": "pplx-7b-online",
            "perplexity-sonar-small-online": "pplx-70b-online"
        }
    
    def get_response(self, model: str, prompt: str) -> str:
        """
        Get response from Perplexity model.
        
        Args:
            model: Perplexity model identifier
            prompt: Input prompt
            
        Returns:
            Model response text
            
        Raises:
            APIError: If API call fails
        """
        if not self.is_available():
            return self.get_config_error_message()
        
        # Map friendly model name to actual API model identifier
        actual_model = self.model_map.get(model, "sonar-small-chat")
        logger.info(f"Making request to Perplexity API with model: {actual_model}")
        logger.info(f"Using endpoint: {self.endpoint}")
        
        try:
            response = requests.post(
                self.endpoint,
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
                timeout=60
            )
            
            # Log response status for debugging
            logger.info(f"Perplexity API response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("Perplexity API request successful")
                return response.json()["choices"][0]["message"]["content"]
            else:
                # More detailed error logging
                error_msg = f"Perplexity API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise APIError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error with Perplexity API: {e}"
            logger.error(error_msg)
            raise APIError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error with Perplexity API: {e}"
            logger.error(error_msg)
            raise APIError(error_msg) from e
    
    def is_available(self) -> bool:
        """Check if Perplexity client is properly configured."""
        return bool(self.api_key)
