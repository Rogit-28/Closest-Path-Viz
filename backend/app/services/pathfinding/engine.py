"""
Pathfinding engine — orchestrates algorithm execution with WebSocket streaming.
"""

import logging
from typing import Optional

import networkx as nx

from app.schemas.pathfinding import (
    AlgorithmType,
    HeuristicType,
    WeightFunction,
    PathfindingConfig,
)
from app.services.pathfinding.base import PathfindingAlgorithm, PathResult
from app.services.pathfinding.dijkstra import DijkstraPathfinder
from app.services.pathfinding.astar import AStarPathfinder
from app.services.pathfinding.bidirectional import BidirectionalDijkstraPathfinder
from app.services.pathfinding.bellman_ford import BellmanFordPathfinder
from app.services.pathfinding.floyd_warshall import FloydWarshallPathfinder
from app.services.pathfinding.yen_k_shortest import YensKShortestPathfinder

logger = logging.getLogger("pathfinding.engine")


def get_algorithm(
    algo_type: AlgorithmType, config: PathfindingConfig
) -> PathfindingAlgorithm:
    """Factory: create algorithm instance based on type and config."""
    if algo_type == AlgorithmType.DIJKSTRA:
        return DijkstraPathfinder()
    elif algo_type == AlgorithmType.ASTAR:
        return AStarPathfinder(heuristic_type=config.astar_heuristic.value)
    elif algo_type == AlgorithmType.BIDIRECTIONAL:
        return BidirectionalDijkstraPathfinder()
    elif algo_type == AlgorithmType.BELLMAN_FORD:
        return BellmanFordPathfinder()
    elif algo_type == AlgorithmType.FLOYD_WARSHALL:
        return FloydWarshallPathfinder()
    else:
        raise ValueError(f"Unknown algorithm: {algo_type}")


def get_weight_key(config: PathfindingConfig) -> str:
    """Determine the edge weight attribute to use."""
    if config.weight_function == WeightFunction.DISTANCE:
        return "distance"
    elif config.weight_function == WeightFunction.TIME:
        return "time"
    elif config.weight_function == WeightFunction.HYBRID:
        return "hybrid"  # will need special handling
    return "distance"


def compute_hybrid_weights(graph: nx.DiGraph, config: PathfindingConfig) -> nx.DiGraph:
    """Pre-compute hybrid edge weights: alpha * distance + beta * time."""
    alpha = config.hybrid_weights.alpha if config.hybrid_weights else 0.6
    beta = config.hybrid_weights.beta if config.hybrid_weights else 0.4

    for u, v, data in graph.edges(data=True):
        dist = data.get("distance", 0)
        time_val = data.get("time", 0)
        # Normalize: distance in km, time in minutes
        data["hybrid"] = alpha * (dist / 1000) + beta * (time_val / 60)

    return graph


async def run_pathfinding(
    graph: nx.DiGraph,
    start: str,
    end: str,
    algo_type: AlgorithmType,
    config: PathfindingConfig,
    websocket=None,
) -> PathResult:
    """
    Execute a single pathfinding algorithm.
    """
    weight_key = get_weight_key(config)

    if weight_key == "hybrid":
        graph = compute_hybrid_weights(graph, config)

    # Handle K-shortest paths
    if config.k_paths > 1:
        algo = YensKShortestPathfinder(k=config.k_paths)
    else:
        algo = get_algorithm(algo_type, config)

    logger.info(
        f"Running {algo.name} from {start} to {end}, "
        f"weight={weight_key}, k={config.k_paths}"
    )

    result = await algo.find_path(
        graph,
        start,
        end,
        weight_key,
        websocket=websocket,
        config={"k_paths": config.k_paths},
    )

    # Stream completion
    if websocket:
        try:
            await websocket.send_json(
                {
                    "type": "complete",
                    "algorithm": result.algorithm,
                    "path": result.path_coords,
                    "metrics": {
                        "nodes_explored": result.nodes_explored,
                        "path_length_km": result.path_length_km,
                        "computation_time_ms": result.computation_time_ms,
                        "memory_usage_mb": result.memory_usage_mb,
                        "cost": result.cost,
                        "path_node_count": len(result.path),
                        "extra": result.extra,
                    },
                    "success": result.success,
                    "error": result.error,
                }
            )
        except Exception:
            pass

    return result


async def run_multi_pathfinding(
    graph: nx.DiGraph,
    start: str,
    end: str,
    algorithms: list[AlgorithmType],
    config: PathfindingConfig,
    websocket=None,
) -> list[PathResult]:
    """
    Execute multiple pathfinding algorithms sequentially (for comparison).
    """
    results = []
    for algo_type in algorithms:
        result = await run_pathfinding(graph, start, end, algo_type, config, websocket)
        results.append(result)
    return results
