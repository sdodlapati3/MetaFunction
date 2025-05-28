"""
AI model interaction service.

This service provides a unified interface for interacting with multiple
AI providers while handling fallbacks, caching, and error management.
"""

import logging
from typing import Dict, List, Optional
from collections import OrderedDict

from app.clients.openai_client import OpenAIClient
from app.clients.deepseek_client import DeepSeekClient
from app.clients.perplexity_client import PerplexityClient
from app.utils.exceptions import ModelNotFoundError, APIError

logger = logging.getLogger(__name__)

class AIService:
    """Service for managing AI model interactions."""
    
    def __init__(self, cache_size: int = 100):
        """
        Initialize AI service.
        
        Args:
            cache_size: Maximum number of cached responses
        """
        self.cache_size = cache_size
        self.query_cache = OrderedDict()
        
        # Initialize clients
        self.clients = {
            'openai': OpenAIClient(),
            'deepseek': DeepSeekClient(),
            'perplexity': PerplexityClient()
        }
        
        # Model routing configuration
        self.model_routing = {
            'gpt-4': 'openai',
            'gpt-4o-mini': 'openai',
            'gpt-4-32k': 'openai',
            'gpt-3.5-turbo': 'openai',
            'gpt-3.5-turbo-16k': 'openai',
            'deepseek-chat': 'deepseek',
            'deepseek-coder': 'deepseek',
            'perplexity-online-llama3': 'perplexity',
            'perplexity-sonar-small-online': 'perplexity'
        }
        
        self.fallback_model = 'gpt-4o-mini'
    
    def get_available_models(self) -> List[str]:
        """Get list of available models based on configured clients."""
        available_models = []
        
        for model, client_name in self.model_routing.items():
            client = self.clients.get(client_name)
            if client and client.is_available():
                available_models.append(model)
        
        # Ensure at least the fallback model is available
        if not available_models and self.fallback_model not in available_models:
            # Check if OpenAI client is available for fallback
            openai_client = self.clients.get('openai')
            if openai_client and openai_client.is_available():
                available_models.append(self.fallback_model)
        
        return available_models
    
    def get_response(self, model: str, prompt: str, 
                    use_cache: bool = True, fallback_on_error: bool = True) -> str:
        """
        Get response from specified AI model.
        
        Args:
            model: Model identifier
            prompt: Input prompt
            use_cache: Whether to use cached responses
            fallback_on_error: Whether to fallback to default model on error
            
        Returns:
            AI model response text
            
        Raises:
            ModelNotFoundError: If model is not available
            APIError: If all attempts fail
        """
        # Check cache first
        if use_cache:
            cache_key = f"{model}:{hash(prompt)}"
            cached_response = self.query_cache.get(cache_key)
            if cached_response:
                logger.info(f"Using cached response for model {model}")
                # Move to end (LRU)
                self.query_cache.move_to_end(cache_key)
                return cached_response
        
        # Get response from model
        try:
            response = self._get_model_response(model, prompt)
            
            # Cache successful response
            if use_cache and response:
                self._add_to_cache(cache_key, response)
            
            return response
            
        except (ModelNotFoundError, APIError) as e:
            logger.error(f"Error with model {model}: {e}")
            
            if fallback_on_error and model != self.fallback_model:
                logger.info(f"Falling back to {self.fallback_model}")
                return self.get_response(
                    self.fallback_model,
                    prompt,
                    use_cache=use_cache,
                    fallback_on_error=False
                )
            else:
                raise
    
    def _get_model_response(self, model: str, prompt: str) -> str:
        """Get response from specific model."""
        client_name = self.model_routing.get(model)
        if not client_name:
            available_models = list(self.model_routing.keys())
            raise ModelNotFoundError(
                f"Model '{model}' not found. Available: {available_models}"
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
    
    def _add_to_cache(self, key: str, value: str) -> None:
        """Add item to cache with size limit."""
        if key in self.query_cache:
            self.query_cache.pop(key)
        elif len(self.query_cache) >= self.cache_size:
            # Remove oldest item
            self.query_cache.popitem(last=False)
        
        self.query_cache[key] = value
    
    def validate_model(self, model: str) -> bool:
        """Check if a model is available."""
        return model in self.get_available_models()
    
    def get_model_info(self, model: str) -> Dict[str, str]:
        """Get information about a specific model."""
        if not self.validate_model(model):
            return {
                'status': 'unavailable',
                'reason': 'Model not configured or client unavailable'
            }
        
        client_name = self.model_routing.get(model)
        client = self.clients.get(client_name)
        
        return {
            'status': 'available',
            'provider': client_name,
            'client_status': 'configured' if client.is_available() else 'misconfigured'
        }
    
    def health_check(self) -> Dict[str, any]:
        """Perform health check on all AI clients."""
        health_status = {
            'overall_status': 'healthy',
            'available_models': len(self.get_available_models()),
            'cache_size': len(self.query_cache),
            'clients': {}
        }
        
        any_unhealthy = False
        for client_name, client in self.clients.items():
            try:
                is_available = client.is_available()
                health_status['clients'][client_name] = {
                    'status': 'healthy' if is_available else 'unhealthy',
                    'configured': is_available
                }
                if not is_available:
                    any_unhealthy = True
            except Exception as e:
                health_status['clients'][client_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                any_unhealthy = True
        
        if any_unhealthy:
            health_status['overall_status'] = 'degraded'
        
        # Check if at least one model is available
        if health_status['available_models'] == 0:
            health_status['overall_status'] = 'unhealthy'
        
        return health_status
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self.query_cache.clear()
        logger.info("AI service cache cleared")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        return {
            'size': len(self.query_cache),
            'max_size': self.cache_size,
            'hit_rate': getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_requests', 1), 1)
        }
