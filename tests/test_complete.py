# Comprehensive test suite for MetaFunction
import pytest
import json
import tempfile
import os
from unittest.mock import patch, Mock
from flask import Flask
from app.main import create_app
from app.services.ai_service import AIService
from app.services.paper_service import PaperService
from app.clients.openai_client import OpenAIClient


class TestMetaFunctionApp:
    """Test cases for the main Flask application."""
    
    @pytest.fixture
    def app(self):
        """Create and configure a test Flask application."""
        app = create_app()
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'OPENAI_API_KEY': 'test-key',
            'REDIS_URL': 'redis://localhost:6379/1'
        })
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client for the Flask application."""
        return app.test_client()
    
    def test_index_page(self, client):
        """Test that the index page loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'MetaFunction' in response.data
    
    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    def test_ready_endpoint(self, client):
        """Test the readiness check endpoint."""
        response = client.get('/ready')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
    
    @patch('app.services.ai_service.AIService.get_response')
    def test_chat_endpoint(self, mock_ai_service, client):
        """Test the chat endpoint with mocked AI service."""
        mock_ai_service.return_value = "Mocked AI response"
        
        response = client.post('/chat', data={
            'message': 'Test query about papers',
            'model': 'gpt-4o-mini'
        })
        
        assert response.status_code == 200
        assert b'Mocked AI response' in response.data
    
    def test_chat_endpoint_validation(self, client):
        """Test chat endpoint input validation."""
        # Test empty message
        response = client.post('/chat', data={
            'message': '',
            'model': 'gpt-4o-mini'
        })
        assert response.status_code == 400
        
        # Test missing model
        response = client.post('/chat', data={
            'message': 'Test query'
        })
        assert response.status_code == 400


class TestAIService:
    """Test cases for the AI service."""
    
    @pytest.fixture
    def ai_service(self):
        """Create an AI service instance for testing."""
        return AIService()
    
    @patch('app.clients.openai_client.OpenAIClient.get_completion')
    def test_get_response_success(self, mock_completion, ai_service):
        """Test successful AI response generation."""
        mock_completion.return_value = "Test AI response"
        
        response = ai_service.get_response(
            query="Test query",
            model="gpt-4o-mini"
        )
        
        assert response == "Test AI response"
        mock_completion.assert_called_once()
    
    @patch('app.clients.openai_client.OpenAIClient.get_completion')
    def test_get_response_fallback(self, mock_completion, ai_service):
        """Test AI service fallback mechanism."""
        # First call fails, second succeeds
        mock_completion.side_effect = [Exception("API Error"), "Fallback response"]
        
        response = ai_service.get_response(
            query="Test query",
            model="unavailable-model"
        )
        
        assert response == "Fallback response"
        assert mock_completion.call_count == 2
    
    def test_validate_model(self, ai_service):
        """Test model validation."""
        assert ai_service.validate_model("gpt-4o-mini") is True
        assert ai_service.validate_model("invalid-model") is False


class TestPaperService:
    """Test cases for the paper service."""
    
    @pytest.fixture
    def paper_service(self):
        """Create a paper service instance for testing."""
        return PaperService()
    
    def test_extract_doi_from_text(self, paper_service):
        """Test DOI extraction from text."""
        text_with_doi = "Check this paper: 10.1038/nature12373"
        doi = paper_service.extract_doi_from_text(text_with_doi)
        assert doi == "10.1038/nature12373"
        
        text_without_doi = "This is just regular text"
        doi = paper_service.extract_doi_from_text(text_without_doi)
        assert doi is None
    
    def test_extract_pmid_from_text(self, paper_service):
        """Test PMID extraction from text."""
        text_with_pmid = "PMID: 23831765"
        pmid = paper_service.extract_pmid_from_text(text_with_pmid)
        assert pmid == "23831765"
        
        text_without_pmid = "No PMID here"
        pmid = paper_service.extract_pmid_from_text(text_without_pmid)
        assert pmid is None
    
    @patch('requests.get')
    def test_resolve_paper_by_doi(self, mock_get, paper_service):
        """Test paper resolution by DOI."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'Test Paper Title',
            'authors': ['Author 1', 'Author 2'],
            'abstract': 'Test abstract'
        }
        mock_get.return_value = mock_response
        
        paper_info = paper_service.resolve_paper_by_doi("10.1038/nature12373")
        
        assert paper_info['title'] == 'Test Paper Title'
        assert len(paper_info['authors']) == 2


class TestOpenAIClient:
    """Test cases for the OpenAI client."""
    
    @pytest.fixture
    def openai_client(self):
        """Create an OpenAI client instance for testing."""
        return OpenAIClient(api_key="test-key")
    
    @patch('openai.ChatCompletion.create')
    def test_get_completion_success(self, mock_create, openai_client):
        """Test successful OpenAI completion."""
        mock_create.return_value = Mock(
            choices=[Mock(message=Mock(content="Test response"))]
        )
        
        response = openai_client.get_completion(
            prompt="Test prompt",
            model="gpt-4o-mini"
        )
        
        assert response == "Test response"
    
    @patch('openai.ChatCompletion.create')
    def test_get_completion_rate_limit(self, mock_create, openai_client):
        """Test rate limit handling."""
        mock_create.side_effect = Exception("Rate limit exceeded")
        
        with pytest.raises(Exception):
            openai_client.get_completion(
                prompt="Test prompt",
                model="gpt-4o-mini"
            )


class TestIntegration:
    """Integration tests for the complete system."""
    
    @pytest.fixture
    def app(self):
        """Create and configure a test Flask application."""
        app = create_app()
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY_TEST', 'test-key'),
            'REDIS_URL': 'redis://localhost:6379/1'
        })
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client for the Flask application."""
        return app.test_client()
    
    @pytest.mark.integration
    def test_full_paper_analysis_workflow(self, client):
        """Test the complete paper analysis workflow."""
        # This test requires actual API keys and should only run in CI
        if not os.getenv('OPENAI_API_KEY_TEST'):
            pytest.skip("Integration test requires OPENAI_API_KEY_TEST")
        
        response = client.post('/chat', data={
            'message': 'Analyze this DOI: 10.1038/nature12373',
            'model': 'gpt-4o-mini'
        })
        
        assert response.status_code == 200
        # Add more specific assertions based on expected response format


class TestSecurity:
    """Security-focused test cases."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for security testing."""
        app = create_app()
        app.config['TESTING'] = True
        return app.test_client()
    
    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection."""
        malicious_input = "'; DROP TABLE users; --"
        response = client.post('/chat', data={
            'message': malicious_input,
            'model': 'gpt-4o-mini'
        })
        # Should not cause server error
        assert response.status_code in [200, 400]
    
    def test_xss_protection(self, client):
        """Test protection against XSS attacks."""
        xss_payload = "<script>alert('xss')</script>"
        response = client.post('/chat', data={
            'message': xss_payload,
            'model': 'gpt-4o-mini'
        })
        # Should not execute script
        assert b"<script>" not in response.data
    
    def test_csrf_protection(self, client):
        """Test CSRF protection (when enabled)."""
        # This would test CSRF token validation
        pass


class TestPerformance:
    """Performance-focused test cases."""
    
    def test_response_time(self, client):
        """Test that responses are returned within acceptable time."""
        import time
        
        start_time = time.time()
        response = client.get('/')
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 2.0  # Should respond within 2 seconds
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get('/')
            results.append(response.status_code)
        
        # Create 10 concurrent threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10


if __name__ == '__main__':
    pytest.main([__file__])
