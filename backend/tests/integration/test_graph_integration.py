"""
Integration tests for pathfinding with real graph data.
Tests algorithms on realistic road network graphs.
"""

import pytest
import networkx as nx
from app.services.pathfinding import get_pathfinder, PathResult
from app.services.benchmarking import GraphGenerator


class TestGraphIntegration:
    """Integration tests with generated and synthetic graphs."""
    
    @pytest.fixture
    def grid_digraph(self):
        """Create a directed grid graph representing a road network."""
        gen = GraphGenerator()
        return gen.grid_graph(10, 10)
    
    @pytest.mark.asyncio
    async def test_dijkstra_grid_graph(self, grid_digraph):
        """Test Dijkstra on grid graph."""
        dijkstra = get_pathfinder("dijkstra")
        start = "node_0_0"
        end = "node_9_9"
        
        result = await dijkstra.find_path(grid_digraph, start, end, weight='distance')
        
        assert isinstance(result, PathResult)
        assert result.success
        assert len(result.path) > 1
        assert result.path[0] == start
        assert result.path[-1] == end
    
    @pytest.mark.asyncio
    async def test_astar_grid_graph(self, grid_digraph):
        """Test A* with multiple heuristics on grid."""
        heuristics = ['manhattan', 'euclidean']
        start = "node_0_0"
        end = "node_9_9"
        
        for heuristic in heuristics:
            astar = get_pathfinder("astar", heuristic_type=heuristic)
            result = await astar.find_path(grid_digraph, start, end, weight='distance')
            assert result.success
            assert len(result.path) > 1
    
    @pytest.mark.asyncio
    async def test_bidirectional_search(self, grid_digraph):
        """Test bidirectional search on grid."""
        bidirectional = get_pathfinder("bidirectional")
        start = "node_0_0"
        end = "node_9_9"
        
        result = await bidirectional.find_path(grid_digraph, start, end, weight='distance')
        
        assert result.success
        assert result.path[0] == start
        assert result.path[-1] == end
    
    @pytest.mark.asyncio
    async def test_algorithm_comparison(self, grid_digraph):
        """Compare all algorithms on the same graph."""
        algorithms = ['dijkstra', 'astar', 'bidirectional']
        start = "node_0_0"
        end = "node_5_5"
        
        results = {}
        for algo_name in algorithms:
            algo = get_pathfinder(algo_name)
            result = await algo.find_path(grid_digraph, start, end, weight='distance')
            results[algo_name] = len(result.path) if result.success else None
        
        # All should find valid paths
        assert all(v is not None for v in results.values())
    
    @pytest.mark.asyncio
    async def test_single_node_path(self):
        """Test start and end are the same node."""
        g = nx.DiGraph()
        g.add_node(0, lat=0, lon=0)
        
        dijkstra = get_pathfinder("dijkstra")
        result = await dijkstra.find_path(g, 0, 0, weight='distance')
        
        assert result.success
        assert result.path == [0]
    
    @pytest.mark.asyncio
    async def test_disconnected_nodes(self):
        """Test when start and end are unreachable."""
        g = nx.DiGraph()
        g.add_node(0, lat=0, lon=0)
        g.add_node(1, lat=1, lon=1)
        # No edges, so 0->1 is unreachable
        
        dijkstra = get_pathfinder("dijkstra")
        result = await dijkstra.find_path(g, 0, 1, weight='distance')
        
        # Should fail (no path)
        assert not result.success or result.path is None
    
    @pytest.mark.asyncio
    async def test_random_graph(self):
        """Test on random graph."""
        gen = GraphGenerator()
        g = gen.random_graph(50, 0.15)
        
        # Get connected nodes
        dijkstra = get_pathfinder("dijkstra")
        
        # Try to find a path (might not exist in random graph)
        nodes = list(g.nodes())
        start, end = nodes[0], nodes[-1]
        
        result = await dijkstra.find_path(g, start, end, weight='distance')
        
        # Just verify we get a valid PathResult
        assert isinstance(result, PathResult)
    
    @pytest.mark.asyncio
    async def test_scale_free_graph(self):
        """Test on scale-free network."""
        gen = GraphGenerator()
        g = gen.scale_free_graph(50)
        
        dijkstra = get_pathfinder("dijkstra")
        nodes = list(g.nodes())
        start, end = nodes[0], nodes[-1]
        
        result = await dijkstra.find_path(g, start, end, weight='distance')
        
        assert isinstance(result, PathResult)


class TestGraphGenerators:
    """Test the graph generation utilities."""
    
    def test_grid_graph_generation(self):
        """Test grid graph generation."""
        gen = GraphGenerator()
        g = gen.grid_graph(10, 10)
        
        assert g.number_of_nodes() == 100
        assert isinstance(g, nx.DiGraph)
    
    def test_random_graph_generation(self):
        """Test random graph generation."""
        gen = GraphGenerator()
        g = gen.random_graph(50, 0.15)
        
        assert g.number_of_nodes() == 50
        assert isinstance(g, nx.DiGraph)
    
    def test_scale_free_graph_generation(self):
        """Test scale-free graph generation."""
        gen = GraphGenerator()
        g = gen.scale_free_graph(50)
        
        assert g.number_of_nodes() == 50
        assert isinstance(g, nx.DiGraph)
    
    def test_all_edges_have_weights(self):
        """Verify all generated graphs have edge weights."""
        gen = GraphGenerator()
        
        for g in [
            gen.grid_graph(5, 5),
            gen.random_graph(20, 0.1),
            gen.scale_free_graph(20),
        ]:
            for u, v, data in g.edges(data=True):
                assert 'distance' in data
                assert data['distance'] > 0


class TestPathResultStructure:
    """Test the PathResult dataclass structure."""
    
    @pytest.mark.asyncio
    async def test_path_result_fields(self):
        """Verify PathResult has all required fields."""
        gen = GraphGenerator()
        g = gen.grid_graph(5, 5)
        
        dijkstra = get_pathfinder("dijkstra")
        result = await dijkstra.find_path(g, "node_0_0", "node_4_4", weight='distance')
        
        assert hasattr(result, 'algorithm')
        assert hasattr(result, 'path')
        assert hasattr(result, 'cost')
        assert hasattr(result, 'nodes_explored')
        assert hasattr(result, 'computation_time_ms')
        assert hasattr(result, 'memory_usage_mb')
        assert hasattr(result, 'success')
        
        assert result.algorithm == 'dijkstra'
        assert isinstance(result.path, list)
        assert isinstance(result.nodes_explored, int)
        assert isinstance(result.computation_time_ms, (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
