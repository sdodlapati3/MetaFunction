#!/usr/bin/env python3
"""
MetaFunction Repository Restructuring Script

This script helps migrate the current monolithic structure to a more modular,
maintainable architecture. Run this script to create the new directory structure
and begin the migration process.

Usage:
    python scripts/restructure.py [--dry-run] [--backup]
    
Options:
    --dry-run    Show what would be done without making changes
    --backup     Create backup of current structure before migrating
"""

import os
import shutil
import argparse
import time
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class RestructureManager:
    def __init__(self, root_dir, dry_run=False, backup=False):
        self.root_dir = Path(root_dir)
        self.dry_run = dry_run
        self.backup = backup
        
    def create_directory_structure(self):
        """Create the new directory structure."""
        directories = [
            # Main application package
            'app',
            'app/models',
            'app/routes', 
            'app/services',
            'app/clients',
            'app/utils',
            
            # Resolvers (migrated from utils/)
            'resolvers',
            
            # Static assets
            'static/css',
            'static/js', 
            'static/images',
            
            # Enhanced templates
            'templates/admin',
            'templates/components',
            
            # Comprehensive testing
            'tests/unit',
            'tests/integration', 
            'tests/fixtures',
            
            # Documentation
            'docs',
            
            # Utility scripts
            'scripts',
            
            # Deployment configs
            'deployment/systemd',
            'deployment/k8s',
        ]
        
        for directory in directories:
            dir_path = self.root_dir / directory
            if self.dry_run:
                logger.info(f"Would create directory: {dir_path}")
            else:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
                
                # Create __init__.py for Python packages
                if any(dir_path.match(pattern) for pattern in ['app*', 'resolvers', 'tests*']):
                    init_file = dir_path / '__init__.py'
                    if not init_file.exists():
                        init_file.touch()
                        logger.info(f"Created __init__.py in {dir_path}")

    def create_config_files(self):
        """Create modern configuration files."""
        config_files = {
            'pyproject.toml': self._get_pyproject_toml(),
            'requirements-dev.txt': self._get_dev_requirements(),
            'Dockerfile': self._get_dockerfile(),
            'docker-compose.yml': self._get_docker_compose(),
            'Makefile': self._get_makefile(),
            '.dockerignore': self._get_dockerignore(),
            'app/config.py': self._get_app_config(),
            'app/__init__.py': self._get_app_init(),
            'tests/conftest.py': self._get_test_config(),
        }
        
        for filename, content in config_files.items():
            file_path = self.root_dir / filename
            if self.dry_run:
                logger.info(f"Would create file: {file_path}")
            else:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content)
                logger.info(f"Created file: {file_path}")

    def _get_pyproject_toml(self):
        return '''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "metafunction"
version = "2.0.0"
description = "AI-powered scientific paper analysis and summarization"
authors = [{name = "Sanjeeva Dodlapati", email = "sdodl001@odu.edu"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.8"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]

dependencies = [
    "flask>=2.3.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=4.9.0",
    "openai>=1.5.0",
    "pdfplumber>=0.9.0",
    "PyMuPDF>=1.23.0",
    "pdfminer.six>=20221105",
    "biopython>=1.81",
    "google-search-results>=2.4.0",
    "selenium>=4.15.0",
    "webdriver-manager>=4.0.0",
    "certifi>=2023.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.0",
    "black>=23.7.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.3.0",
]

[project.urls]
Homepage = "https://github.com/SanjeevaRDodlapati/MetaFunction"
Repository = "https://github.com/SanjeevaRDodlapati/MetaFunction"
Issues = "https://github.com/SanjeevaRDodlapati/MetaFunction/issues"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*", "resolvers*"]

[tool.black]
line-length = 88
target-version = ['py38']
include = '\\.pyi?$'

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=app --cov=resolvers --cov-report=html --cov-report=term-missing"

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
'''

    def _get_dev_requirements(self):
        return '''# Development dependencies
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
black>=23.7.0
flake8>=6.0.0
mypy>=1.5.0
pre-commit>=3.3.0
httpx>=0.24.0  # For testing async HTTP calls
factory-boy>=3.3.0  # For creating test fixtures
'''

    def _get_dockerfile(self):
        return '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    wget \\
    gnupg \\
    unzip \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \\
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \\
    && apt-get update \\
    && apt-get install -y google-chrome-stable \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app.main:create_app()"]
'''

    def _get_docker_compose(self):
        return '''version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=development
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - PERPLEXITY_API_KEY=${PERPLEXITY_API_KEY}
    volumes:
      - .:/app
      - ./logs:/app/logs
    command: flask run --host=0.0.0.0 --port=8000 --debug

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
'''

    def _get_makefile(self):
        return '''# MetaFunction Development Makefile

.PHONY: help install install-dev test lint format clean run docker-build docker-run

help: ## Show this help message
\t@echo "Available commands:"
\t@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\\033[36m%-20s\\033[0m %s\\n", $$1, $$2}'

install: ## Install production dependencies
\tpip install -r requirements.txt

install-dev: ## Install development dependencies
\tpip install -r requirements.txt -r requirements-dev.txt
\tpre-commit install

test: ## Run tests
\tpytest tests/ -v

test-cov: ## Run tests with coverage
\tpytest tests/ -v --cov=app --cov=resolvers --cov-report=html

lint: ## Run linting
\tflake8 app/ resolvers/ tests/
\tmypy app/ resolvers/

format: ## Format code
\tblack app/ resolvers/ tests/

clean: ## Clean up temporary files
\tfind . -type f -name "*.pyc" -delete
\tfind . -type d -name "__pycache__" -delete
\trm -rf .coverage htmlcov/ .pytest_cache/

run: ## Run the application in development mode
\tFLASK_ENV=development flask run --host=0.0.0.0 --port=8000 --debug

docker-build: ## Build Docker image
\tdocker build -t metafunction .

docker-run: ## Run Docker container
\tdocker run -p 8000:8000 --env-file .env metafunction

migrate: ## Run data migration
\tpython scripts/migrate_data.py

benchmark: ## Run performance benchmarks
\tpython scripts/benchmark_resolvers.py
'''

    def _get_dockerignore(self):
        return '''.git
.gitignore
README.md
Dockerfile
docker-compose.yml
.dockerignore
.env*
.venv/
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
htmlcov/
logs/
*.log
.DS_Store
'''

    def _get_app_config(self):
        return '''"""Application configuration management."""

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
'''

    def _get_app_init(self):
        return '''"""MetaFunction Application Package."""

__version__ = "2.0.0"
__author__ = "Sanjeeva Dodlapati"
__email__ = "sdodl001@odu.edu"

# Export main factory function
from .main import create_app

__all__ = ['create_app']
'''

    def _get_test_config(self):
        return '''"""Test configuration and fixtures."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from app import create_app
from app.config import TestingConfig

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app(TestingConfig)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test AI response"
    return mock_response

@pytest.fixture
def sample_paper_metadata():
    """Sample paper metadata for testing."""
    return {
        "title": "Sample Research Paper",
        "authors": ["John Doe", "Jane Smith"],
        "journal": "Test Journal",
        "year": "2023",
        "doi": "10.1000/test.doi",
        "pmid": "12345678",
        "abstract": "This is a test abstract.",
        "has_full_text": True,
        "pdf_url": "https://example.com/paper.pdf"
    }

@pytest.fixture
def mock_requests():
    """Mock requests for external API calls."""
    with patch('requests.get') as mock_get, \\
         patch('requests.post') as mock_post:
        yield {'get': mock_get, 'post': mock_post}
'''

    def backup_current_structure(self):
        """Create backup of current structure."""
        if not self.backup:
            return
            
        backup_dir = self.root_dir / f"backup_{int(time.time())}"
        if self.dry_run:
            logger.info(f"Would create backup at: {backup_dir}")
        else:
            shutil.copytree(self.root_dir, backup_dir, ignore=shutil.ignore_patterns('backup_*'))
            logger.info(f"Created backup at: {backup_dir}")

    def run(self):
        """Execute the restructuring process."""
        logger.info("Starting MetaFunction repository restructuring...")
        
        if self.backup:
            self.backup_current_structure()
            
        self.create_directory_structure()
        self.create_config_files()
        
        logger.info("Restructuring complete!")
        logger.info("Next steps:")
        logger.info("1. Review the new structure")
        logger.info("2. Run 'make install-dev' to set up development environment")
        logger.info("3. Begin migrating code from app.py to the new modules")
        logger.info("4. Set up testing with 'make test'")

def main():
    parser = argparse.ArgumentParser(description='Restructure MetaFunction repository')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup before restructuring')
    parser.add_argument('--root', default='.',
                       help='Root directory of the project (default: current directory)')
    
    args = parser.parse_args()
    
    restructure_manager = RestructureManager(
        root_dir=args.root,
        dry_run=args.dry_run,
        backup=args.backup
    )
    
    restructure_manager.run()

if __name__ == '__main__':
    main()
