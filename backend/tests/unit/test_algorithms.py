"""Unit tests for all pathfinding algorithms."""

import pytest
import asyncio
import networkx as nx

from app.services.pathfinding import (
    DijkstraPathfinder,
    AStarPathfinder,
    BidirectionalDijkstraPathfinder,
    BellmanFordPathfinder,
    FloydWarshallPathfinder,
    YensKShortestPathfinder,
    get_pathfinder,
)


@pytest.fixture
def simple_graph():
    """Simple 5-node graph with known shortest paths."""
    g = nx.DiGraph()
    g.add_node("A", lat=0.0, lon=0.0)
    g.add_node("B", lat=1.0, lon=0.0)
    g.add_node("C", lat=1.0, lon=1.0)
    g.add_node("D", lat=2.0, lon=1.0)
    g.add_node("E", lat=2.0, lon=0.0)
    
    g.add_edge("A", "B", distance=1.0)
    g.add_edge("B", "C", distance=1.0)
    g.add_edge("A", "E", distance=4.0)
    g.add_edge("C", "D", distance=1.0)
    g.add_edge("E", "D", distance=1.0)
    
    return g


@pytest.fixture
def disconnected_graph():
    """Graph with disconnected components."""
    g = nx.DiGraph()
    g.add_node("A", lat=0.0, lon=0.0)
    g.add_node("B", lat=1.0, lon=0.0)
    g.add_node("C", lat=2.0, lon=0.0)
    g.add_node("D", lat=3.0, lon=0.0)
    
    g.add_edge("A", "B", distance=1.0)
    g.add_edge("C", "D", distance=1.0)
    
    return g


@pytest.mark.asyncio
async def test_dijkstra_simple_path(simple_graph):
    """Test Dijkstra finds correct shortest path."""
    dijkstra = DijkstraPathfinder()
    result = await dijkstra.find_path(simple_graph, "A", "D", "distance")
    
    assert result.success
    assert result.path == ["A", "B", "C", "D"]
    assert result.cost == 3.0


@pytest.mark.asyncio
async def test_dijkstra_same_node(simple_graph):
    """Test Dijkstra with start == end."""
    dijkstra = DijkstraPathfinder()
    result = await dijkstra.find_path(simple_graph, "A", "A", "distance")
    
    assert result.success
    assert result.path == ["A"]
    assert result.cost == 0.0


@pytest.mark.asyncio
async def test_dijkstra_no_path(disconnected_graph):
    """Test Dijkstra when no path exists."""
    dijkstra = DijkstraPathfinder()
    result = await dijkstra.find_path(disconnected_graph, "A", "D", "distance")
    
    assert not result.success
    assert result.path == []


@pytest.mark.asyncio
async def test_astar_haversine(simple_graph):
    """Test A* with haversine heuristic."""
    astar = AStarPathfinder(heuristic_type="haversine")
    result = await astar.find_path(simple_graph, "A", "D", "distance")
    
    assert result.success
    assert len(result.path) > 0


@pytest.mark.asyncio
async def test_astar_invalid_heuristic():
    """Test A* rejects invalid heuristic."""
    with pytest.raises(ValueError):
        AStarPathfinder(heuristic_type="invalid")


@pytest.mark.asyncio
async def test_bidirectional_path(simple_graph):
    """Test bidirectional search finds correct path."""
    bidirectional = BidirectionalDijkstraPathfinder()
    result = await bidirectional.find_path(simple_graph, "A", "D", "distance")
    
    assert result.success
    assert result.path[0] == "A"
    assert result.path[-1] == "D"


@pytest.mark.asyncio
async def test_bellman_ford_simple(simple_graph):
    """Test Bellman-Ford finds correct path."""
    bellman = BellmanFordPathfinder()
    result = await bellman.find_path(simple_graph, "A", "D", "distance")
    
    assert result.success
    assert len(result.path) > 0


@pytest.mark.asyncio
async def test_floyd_warshall_simple(simple_graph):
    """Test Floyd-Warshall finds correct path."""
    fw = FloydWarshallPathfinder()
    result = await fw.find_path(simple_graph, "A", "D", "distance")
    
    assert result.success
    assert len(result.path) > 0


@pytest.mark.asyncio
async def test_yens_single_path(simple_graph):
    """Test Yen's returns at least one path."""
    yens = YensKShortestPathfinder(k=1)
    result = await yens.find_path(simple_graph, "A", "D", "distance")
    
    assert result.success
    assert len(result.path) > 0


def test_factory_dijkstra():
    """Test factory returns Dijkstra."""
    pathfinder = get_pathfinder("dijkstra")
    assert isinstance(pathfinder, DijkstraPathfinder)


def test_factory_astar():
    """Test factory returns A*."""
    pathfinder = get_pathfinder("astar")
    assert isinstance(pathfinder, AStarPathfinder)


def test_factory_invalid():
    """Test factory rejects invalid algorithm."""
    with pytest.raises(ValueError):
        get_pathfinder("invalid_algorithm")
