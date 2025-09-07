"""Pathfinding services module."""

from app.services.pathfinding.base import PathfindingAlgorithm, PathResult
from app.services.pathfinding.dijkstra import DijkstraPathfinder
from app.services.pathfinding.astar import AStarPathfinder
from app.services.pathfinding.bidirectional import BidirectionalDijkstraPathfinder
from app.services.pathfinding.bellman_ford import BellmanFordPathfinder
from app.services.pathfinding.floyd_warshall import FloydWarshallPathfinder
from app.services.pathfinding.yens_k_shortest import YensKShortestPathfinder

__all__ = [
    "PathfindingAlgorithm",
    "PathResult",
    "DijkstraPathfinder",
    "AStarPathfinder",
    "BidirectionalDijkstraPathfinder",
    "BellmanFordPathfinder",
    "FloydWarshallPathfinder",
    "YensKShortestPathfinder",
]

# Factory function for getting algorithm by name
ALGORITHM_REGISTRY = {
    "dijkstra": DijkstraPathfinder,
    "astar": AStarPathfinder,
    "bidirectional": BidirectionalDijkstraPathfinder,
    "bellman_ford": BellmanFordPathfinder,
    "floyd_warshall": FloydWarshallPathfinder,
    "yens_k_shortest": YensKShortestPathfinder,
}


def get_pathfinder(algorithm_name: str, **kwargs):
    """Get pathfinder instance by name.
    
    Args:
        algorithm_name: One of {dijkstra, astar, bidirectional, bellman_ford, floyd_warshall, yens_k_shortest}
        **kwargs: Algorithm-specific configuration (e.g., heuristic_type='haversine' for astar, k=5 for yens_k_shortest)
    
    Returns:
        Initialized pathfinder instance
        
    Raises:
        ValueError: If algorithm_name not in registry
    """
    if algorithm_name not in ALGORITHM_REGISTRY:
        raise ValueError(
            f"Unknown algorithm: {algorithm_name}. "
            f"Available: {list(ALGORITHM_REGISTRY.keys())}"
        )
    
    algorithm_class = ALGORITHM_REGISTRY[algorithm_name]
    return algorithm_class(**kwargs)
