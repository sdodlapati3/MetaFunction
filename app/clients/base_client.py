"""
Base client interface for AI providers.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAIClient(ABC):
    """Abstract base class for AI clients."""
    
    def __init__(self, api_key_env_var: str):
        """
        Initialize base client.
        
        Args:
            api_key_env_var: Environment variable name for the API key
        """
        self.api_key = os.getenv(api_key_env_var)
        self.api_key_env_var = api_key_env_var
    
    @abstractmethod
    def get_response(self, model: str, prompt: str) -> str:
        """
        Get response from AI model.
        
        Args:
            model: Model identifier
            prompt: Input prompt
            
        Returns:
            AI model response
            
        Raises:
            APIError: If the API call fails
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if the client is properly configured.
        
        Returns:
            True if client is configured and ready to use
        """
        return bool(self.api_key)
    
    def get_config_error_message(self) -> str:
        """
        Get error message for missing configuration.
        
        Returns:
            Descriptive error message
        """
        return f"{self.__class__.__name__} API key not configured. Please add {self.api_key_env_var} to your .env file."
