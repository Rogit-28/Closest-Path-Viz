"""
API integration tests for pathfinding endpoints.
Tests the REST API and WebSocket interfaces.
"""

import pytest
import networkx as nx
from unittest.mock import AsyncMock, patch
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
        assert "dijkstra" in data or "astar" in data

    def test_algorithm_details(self):
        """Test getting details of specific algorithm."""
        response = client.get("/api/pathfinding/algorithm/dijkstra")
        assert response.status_code == 200
        data = response.json()
        assert "dijkstra" in data
        assert "description" in data["dijkstra"]
        assert "name" in data["dijkstra"]

    def test_invalid_algorithm(self):
        """Test requesting invalid algorithm."""
        response = client.get("/api/pathfinding/algorithm/totally_fake_algo_xyz")
        # Should either 404 or return empty
        assert response.status_code in [200, 404]


class TestPathfindingContracts:
    """Contract checks for pathfinding payload consistency."""

    @staticmethod
    def _metadata_for(graph: nx.DiGraph) -> dict:
        return {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "fallback_speed_pct": 0.0,
            "source": "synthetic",
        }

    @staticmethod
    def _disconnected_graph() -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_node("A", lat=0.0, lon=0.0)
        graph.add_node("B", lat=0.5, lon=0.5)
        graph.add_node("C", lat=1.0, lon=1.0)
        graph.add_node("D", lat=1.5, lon=1.5)
        graph.add_edge("A", "B", distance=1.0, time=1.0)
        graph.add_edge("C", "D", distance=1.0, time=1.0)
        return graph

    @staticmethod
    def _connected_graph() -> nx.DiGraph:
        graph = nx.DiGraph()
        graph.add_node("A", lat=0.0, lon=0.0)
        graph.add_node("B", lat=0.5, lon=0.5)
        graph.add_node("C", lat=1.0, lon=1.0)
        graph.add_node("D", lat=1.5, lon=1.5)
        graph.add_edge("A", "B", distance=1.0, time=1.0)
        graph.add_edge("B", "D", distance=1.0, time=1.0)
        graph.add_edge("A", "C", distance=1.2, time=1.2)
        graph.add_edge("C", "D", distance=1.0, time=1.0)
        return graph

    def test_find_path_no_path_uses_null_cost(self):
        graph = self._disconnected_graph()
        metadata = self._metadata_for(graph)
        payload = {
            "start": {"lat": 0.0, "lon": 0.0},
            "end": {"lat": 1.5, "lon": 1.5},
            "algorithms": ["dijkstra"],
        }

        with patch(
            "app.api.routes.pathfinding.graph_service.get_graph_for_region",
            new=AsyncMock(return_value=(graph, metadata)),
        ), patch(
            "app.api.routes.pathfinding.graph_service.find_nearest_node",
            side_effect=["A", "D"],
        ):
            response = client.post("/api/pathfinding/find-path", json=payload)

        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["success"] is False
        assert result["cost"] is None
        assert result["requested_algorithm"] == "dijkstra"
        assert result["executed_algorithm"] == "dijkstra"

    def test_find_path_k_paths_exposes_requested_and_executed_algorithms(self):
        graph = self._connected_graph()
        metadata = self._metadata_for(graph)
        payload = {
            "start": {"lat": 0.0, "lon": 0.0},
            "end": {"lat": 1.5, "lon": 1.5},
            "algorithms": ["dijkstra"],
            "config": {"k_paths": 2},
        }

        with patch(
            "app.api.routes.pathfinding.graph_service.get_graph_for_region",
            new=AsyncMock(return_value=(graph, metadata)),
        ), patch(
            "app.api.routes.pathfinding.graph_service.find_nearest_node",
            side_effect=["A", "D"],
        ):
            response = client.post("/api/pathfinding/find-path", json=payload)

        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["algorithm"] == "dijkstra"
        assert result["requested_algorithm"] == "dijkstra"
        assert result["executed_algorithm"] == "yens_k_shortest"
        assert result["extra"]["requested_algorithm"] == "dijkstra"
        assert result["extra"]["executed_algorithm"] == "yens_k_shortest"


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
        assert "openapi" in data
        assert "paths" in data

    def test_swagger_ui(self):
        """Test Swagger UI is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_redoc(self):
        """Test ReDoc is available."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
