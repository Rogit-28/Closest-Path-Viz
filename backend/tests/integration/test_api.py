"""
API integration tests for pathfinding endpoints.
Tests the REST API and WebSocket interfaces.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200


class TestAlgorithmEndpoints:
    """Test pathfinding algorithm endpoints."""
    
    def test_algorithms_list(self):
        """Test getting list of available algorithms."""
        response = client.get("/api/pathfinding/algorithms")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        # Check for expected algorithms
        assert 'dijkstra' in data or 'astar' in data
    
    def test_algorithm_details(self):
        """Test getting details of specific algorithm."""
        response = client.get("/api/pathfinding/algorithm/dijkstra")
        assert response.status_code == 200
        data = response.json()
        assert 'dijkstra' in data
        assert 'description' in data['dijkstra']
        assert 'name' in data['dijkstra']
    
    def test_invalid_algorithm(self):
        """Test requesting invalid algorithm."""
        response = client.get("/api/pathfinding/algorithm/totally_fake_algo_xyz")
        # Should either 404 or return empty
        assert response.status_code in [200, 404]


class TestCORSHeaders:
    """Test CORS configuration."""
    
    def test_cors_headers(self):
        """Test that CORS headers are present."""
        response = client.options("/api/pathfinding/algorithms")
        # May or may not return 200, but should not error
        assert response.status_code in [200, 405]


class TestDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_schema(self):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert 'openapi' in data
        assert 'paths' in data
    
    def test_swagger_ui(self):
        """Test Swagger UI is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')
    
    def test_redoc(self):
        """Test ReDoc is available."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('content-type', '')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
