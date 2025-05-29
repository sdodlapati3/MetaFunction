"""Test configuration and fixtures."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from app.main import create_app
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
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        yield {'get': mock_get, 'post': mock_post}
