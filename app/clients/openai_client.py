"""
OpenAI API client implementation.
"""

import os
import re
import time
import random
import logging
from typing import Optional

import openai

from .base_client import BaseAIClient
from app.utils.exceptions import APIError

logger = logging.getLogger(__name__)


class OpenAIClient(BaseAIClient):
    """OpenAI API client with retry logic and error handling."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        super().__init__('OPENAI_API_KEY')
        
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def get_response(self, model: str, prompt: str) -> str:
        """
        Get response from OpenAI model with retry logic.
        
        Args:
            model: OpenAI model identifier (e.g., 'gpt-4o-mini', 'gpt-4')
            prompt: Input prompt
            
        Returns:
            Model response text
            
        Raises:
            APIError: If API call fails after retries
        """
        if not self.is_available():
            return self.get_config_error_message()
        
        try:
            response = self._safe_create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"Error with OpenAI API: {e}"
            logger.error(error_msg)
            raise APIError(error_msg) from e
    
    def _safe_create(self, **kwargs):
        """
        Safely create a request to OpenAI API with retries.
        
        Args:
            **kwargs: Arguments to pass to the OpenAI API
            
        Returns:
            OpenAI API response
            
        Raises:
            APIError: If all retries are exhausted
        """
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(**kwargs)
                
            except openai.RateLimitError as e:
                retry_after = 20  # Default retry time
                
                # Extract retry time from error message if available
                if "Please try again in" in str(e):
                    try:
                        retry_after = float(
                            re.search(r"try again in ([\d.]+)", str(e)).group(1)
                        )
                    except (AttributeError, ValueError):
                        pass
                
                # Add jitter to avoid thundering herd
                sleep_time = retry_after + (random.random() * 0.5)
                logger.info(f"Rate limit hit, retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error during OpenAI API call (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        raise APIError("Max retries exceeded for OpenAI API call")
    
    def is_available(self) -> bool:
        """Check if OpenAI client is properly configured."""
        return bool(self.api_key and self.client)
