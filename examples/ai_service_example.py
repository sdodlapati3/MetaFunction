"""
Example: AI Service Module - Shows how the new modular structure would work

This is an example of how the AI interaction logic from app.py would be
restructured into a focused, testable service module.
"""

from typing import Dict, Optional, Union
import logging
from abc import ABC, abstractmethod

from app.clients.openai_client import OpenAIClient
from app.clients.deepseek_client import DeepSeekClient
from app.clients.perplexity_client import PerplexityClient
from app.services.cache_service import CacheService
from app.utils.exceptions import ModelNotFoundError, APIError

logger = logging.getLogger(__name__)

class BaseAIClient(ABC):
    """Abstract base class for AI clients."""
    
    @abstractmethod
    def get_response(self, model: str, prompt: str) -> str:
        """Get response from AI model."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        pass

class AIService:
    """
    Service for managing AI model interactions.
    
    This service provides a unified interface for interacting with multiple
    AI providers while handling fallbacks, caching, and error management.
    """
    
    def __init__(self, cache_service: CacheService = None):
        """Initialize AI service with clients and cache."""
        self.cache_service = cache_service or CacheService()
        self.clients: Dict[str, BaseAIClient] = {
            'openai': OpenAIClient(),
            'deepseek': DeepSeekClient(),
            'perplexity': PerplexityClient()
        }
        
        # Model mapping for client routing
        self.model_routing = {
            'gpt-4': 'openai',
            'gpt-4o-mini': 'openai',
            'gpt-3.5-turbo': 'openai',
            'deepseek-chat': 'deepseek',
            'deepseek-coder': 'deepseek',
            'perplexity-online-llama3': 'perplexity',
            'perplexity-sonar-small-online': 'perplexity'
        }
        
        self.fallback_model = 'gpt-4o-mini'
        
    def get_available_models(self) -> list[str]:
        """Get list of available models based on configured clients."""
        available_models = []
        
        for model, client_name in self.model_routing.items():
            client = self.clients.get(client_name)
            if client and client.is_available():
                available_models.append(model)
                
        return available_models
    
    def get_response(
        self, 
        model: str, 
        prompt: str, 
        use_cache: bool = True,
        fallback_on_error: bool = True
    ) -> str:
        """
        Get response from specified AI model.
        
        Args:
            model: Model identifier (e.g., 'gpt-4', 'deepseek-chat')
            prompt: Input prompt for the model
            use_cache: Whether to use cached responses
            fallback_on_error: Whether to fallback to default model on error
            
        Returns:
            AI model response text
            
        Raises:
            ModelNotFoundError: If model is not available
            APIError: If all attempts fail and fallback is disabled
        """
        # Check cache first
        if use_cache:
            cache_key = f"{model}:{hash(prompt)}"
            cached_response = self.cache_service.get(cache_key)
            if cached_response:
                logger.info(f"Using cached response for model {model}")
                return cached_response
        
        # Get response from model
        try:
            response = self._get_model_response(model, prompt)
            
            # Cache successful response
            if use_cache and response:
                self.cache_service.set(cache_key, response)
                
            return response
            
        except (ModelNotFoundError, APIError) as e:
            logger.error(f"Error with model {model}: {e}")
            
            if fallback_on_error and model != self.fallback_model:
                logger.info(f"Falling back to {self.fallback_model}")
                return self.get_response(
                    self.fallback_model, 
                    prompt, 
                    use_cache=use_cache,
                    fallback_on_error=False  # Prevent infinite recursion
                )
            else:
                raise
    
    def _get_model_response(self, model: str, prompt: str) -> str:
        """Get response from specific model."""
        client_name = self.model_routing.get(model)
        if not client_name:
            available_models = list(self.model_routing.keys())
            raise ModelNotFoundError(
                f"Model '{model}' not found. Available models: {available_models}"
            )
        
        client = self.clients.get(client_name)
        if not client:
            raise ModelNotFoundError(f"Client '{client_name}' not initialized")
            
        if not client.is_available():
            raise APIError(f"Client '{client_name}' is not properly configured")
        
        try:
            response = client.get_response(model, prompt)
            logger.info(f"Successfully got response from {model}")
            return response
            
        except Exception as e:
            error_msg = f"Error getting response from {model}: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg) from e
    
    def validate_model(self, model: str) -> bool:
        """Check if a model is available and configured."""
        return model in self.get_available_models()
    
    def get_model_info(self, model: str) -> Dict[str, str]:
        """Get information about a specific model."""
        if not self.validate_model(model):
            return {"status": "unavailable", "reason": "Model not configured"}
            
        client_name = self.model_routing.get(model)
        client = self.clients.get(client_name)
        
        return {
            "status": "available",
            "provider": client_name,
            "client_status": "configured" if client.is_available() else "misconfigured"
        }
    
    def health_check(self) -> Dict[str, any]:
        """Perform health check on all AI clients."""
        health_status = {
            "overall_status": "healthy",
            "available_models": len(self.get_available_models()),
            "clients": {}
        }
        
        for client_name, client in self.clients.items():
            try:
                is_available = client.is_available()
                health_status["clients"][client_name] = {
                    "status": "healthy" if is_available else "unhealthy",
                    "configured": is_available
                }
            except Exception as e:
                health_status["clients"][client_name] = {
                    "status": "error",
                    "error": str(e)
                }
                health_status["overall_status"] = "degraded"
        
        return health_status

# Example usage and testing
if __name__ == "__main__":
    # This shows how the service would be used
    from app.services.cache_service import CacheService
    
    # Initialize services
    cache = CacheService()
    ai_service = AIService(cache)
    
    # Check available models
    models = ai_service.get_available_models()
    print(f"Available models: {models}")
    
    # Get response with fallback
    try:
        response = ai_service.get_response(
            model="gpt-4o-mini",
            prompt="Explain the significance of this paper in 100 words.",
            use_cache=True
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Health check
    health = ai_service.health_check()
    print(f"Health status: {health}")
