"""
Pathfinding engine — orchestrates algorithm execution with WebSocket streaming.
"""

import logging
from typing import Optional, Callable

import networkx as nx

from app.core.config import settings
from app.core.metrics import metrics
from app.schemas.pathfinding import (
    AlgorithmType,
    WeightFunction,
    PathfindingConfig,
)
from app.services.graph.graph_service import graph_service
from app.services.pathfinding.base import PathfindingAlgorithm, PathResult
from app.services.pathfinding.dijkstra import DijkstraPathfinder
from app.services.pathfinding.astar import AStarPathfinder
from app.services.pathfinding.bidirectional import BidirectionalDijkstraPathfinder
from app.services.pathfinding.bellman_ford import BellmanFordPathfinder
from app.services.pathfinding.floyd_warshall import FloydWarshallPathfinder
from app.services.pathfinding.yens_k_shortest import YensKShortestPathfinder
from app.services.pathfinding.serialization import serialize_result_payload

logger = logging.getLogger("pathfinding.engine")


def build_weight_resolver(
    config: PathfindingConfig,
) -> tuple[str, Optional[Callable[[dict], float]]]:
    """Build a safe per-request edge weight resolver without mutating shared graphs."""
    weight_key = get_weight_key(config)
    if weight_key != "hybrid":
        return weight_key, None

    alpha = config.hybrid_weights.alpha if config.hybrid_weights else 0.6
    beta = config.hybrid_weights.beta if config.hybrid_weights else 0.4

    def hybrid_resolver(edge_data: dict) -> float:
        dist = float(edge_data.get("distance", 0))
        time_val = float(edge_data.get("time", 0))
        return alpha * (dist / 1000) + beta * (time_val / 60)

    return "hybrid", hybrid_resolver


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
    weight_key, hybrid_resolver = build_weight_resolver(config)
    floyd_warning: Optional[str] = None

    # Get Floyd-Warshall limit from config or use default
    floyd_limit = getattr(
        config, "floyd_warshall_node_limit", settings.FLOYD_WARSHALL_NODE_LIMIT
    )

    if (
        algo_type == AlgorithmType.FLOYD_WARSHALL
        and graph.number_of_nodes() > floyd_limit
    ):
        graph, subgraph_meta = graph_service.get_endpoint_subgraph(
            graph, start, end, floyd_limit
        )
        floyd_warning = (
            f"Floyd-Warshall ran on {subgraph_meta['selected_nodes']} nodes "
            f"from a {subgraph_meta['full_nodes']} node graph "
            f"(limit: {floyd_limit})."
        )
        logger.warning(floyd_warning)
        if websocket is not None:
            try:
                await websocket.send_json(
                    {
                        "type": "warning",
                        "algorithm": algo_type.value,
                        "message": floyd_warning,
                    }
                )
            except Exception:
                pass

    requested_algorithm = algo_type.value

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
        config={
            "k_paths": config.k_paths,
            "hybrid_resolver": hybrid_resolver,
            "animation_speed": config.animation_speed,
            "animation_granularity": config.animation_granularity.value,
            "show_all_explored": config.show_all_explored,
            "event_algorithm": requested_algorithm,
        },
    )

    # Flush buffered visualization events with animation delays
    # This happens AFTER algorithm completes, so timing is accurate
    await algo._flush_events(websocket)

    if floyd_warning:
        result.extra = result.extra or {}
        warnings = list(result.extra.get("warnings", []))
        warnings.append(floyd_warning)
        result.extra["warnings"] = warnings

    result.extra = result.extra or {}
    result.extra.setdefault("requested_algorithm", requested_algorithm)
    result.extra.setdefault("executed_algorithm", result.algorithm)

    # Record algorithm metrics
    metrics.record_algorithm_run(result.algorithm, result.computation_time_ms)

    # Stream completion
    if websocket:
        try:
            payload = serialize_result_payload(
                result,
                requested_algorithm=requested_algorithm,
                executed_algorithm=result.algorithm,
            )
            await websocket.send_json(
                {
                    "type": "complete",
                    **payload,
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
