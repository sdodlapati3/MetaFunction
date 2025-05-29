"""
Performance testing with Locust for MetaFunction application.
"""
from locust import HttpUser, task, between
import random
import json


class MetaFunctionUser(HttpUser):
    """Simulate user interactions with MetaFunction application."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts."""
        # Test if the application is running
        response = self.client.get("/")
        if response.status_code != 200:
            print(f"Application not responding correctly: {response.status_code}")
    
    @task(3)
    def view_homepage(self):
        """Test loading the main page."""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def view_static_resources(self):
        """Test loading static resources."""
        static_files = [
            "/static/favicon.ico",
            "/static/css/style.css",
            "/static/js/app.js"
        ]
        
        for static_file in random.sample(static_files, 1):
            with self.client.get(static_file, catch_response=True) as response:
                if response.status_code in [200, 404]:  # 404 is acceptable for missing files
                    response.success()
                else:
                    response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def test_chat_endpoint(self):
        """Test the chat endpoint with sample data."""
        test_data = {
            "paper_text": "This is a sample paper text for testing purposes. " * 10,
            "model": "gpt-4o-mini",
            "analysis_focus": "methodology"
        }
        
        with self.client.post("/chat", 
                            data=test_data,
                            catch_response=True) as response:
            if response.status_code in [200, 302]:  # Allow redirects
                response.success()
            elif response.status_code == 400:
                # Bad request is acceptable for test data
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def test_api_health(self):
        """Test API health endpoint if it exists."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code in [200, 404]:  # 404 is acceptable if endpoint doesn't exist
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class APIUser(HttpUser):
    """Test API endpoints specifically."""
    
    wait_time = between(0.5, 2)
    
    @task
    def test_api_endpoints(self):
        """Test various API endpoints."""
        endpoints = [
            "/api/health",
            "/api/status",
            "/api/models"
        ]
        
        for endpoint in endpoints:
            with self.client.get(endpoint, catch_response=True) as response:
                if response.status_code in [200, 404, 405]:  # Allow not found/method not allowed
                    response.success()
                else:
                    response.failure(f"Got status code {response.status_code}")


# Configuration for different load testing scenarios
class LightUser(MetaFunctionUser):
    """Light load user simulation."""
    weight = 3
    wait_time = between(2, 5)


class HeavyUser(MetaFunctionUser):
    """Heavy load user simulation."""
    weight = 1
    wait_time = between(0.5, 1.5)
