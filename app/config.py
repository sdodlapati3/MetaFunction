"""Application configuration management."""

import os
from typing import Dict, Any
from pathlib import Path

class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    TEMPLATES_AUTO_RELOAD = True
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')  # Fixed naming consistency
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY')
    
    # Academic API Keys
    NCBI_EMAIL = os.getenv('NCBI_EMAIL', 'sdodl001@odu.edu')
    CROSSREF_EMAIL = os.getenv('CROSSREF_EMAIL', NCBI_EMAIL)
    SCOPUS_API_KEY = os.getenv('SCOPUS_API_KEY')
    SPRINGER_API_KEY = os.getenv('SPRINGER_API_KEY')
    
    # Application settings
    BASE_DIR = Path(__file__).parent.parent
    LOG_DIR = BASE_DIR / 'logs'
    CACHE_SIZE = int(os.getenv('CACHE_SIZE', '100'))
    
    # Model settings
    DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-4o-mini')
    MAX_TEXT_LENGTH = int(os.getenv('MAX_TEXT_LENGTH', '10000'))
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
    
    @classmethod
    def init_app(cls, app):
        """Initialize application with this config."""
        # Ensure log directory exists
        cls.LOG_DIR.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Use environment variables for security in production
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be set in production")

class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    
    # Use in-memory cache for testing
    CACHE_SIZE = 10

# Configuration mapping
config_map: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Config:
    """Get configuration based on environment."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    return config_map.get(config_name, DevelopmentConfig)
