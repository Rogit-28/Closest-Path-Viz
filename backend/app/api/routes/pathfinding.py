"""
Pathfinding API endpoints.

Provides REST endpoints for computing shortest paths using various algorithms.
Real-time node visitation is streamed via WebSocket if connected.
"""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.pathfinding import (
    AlgorithmType,
    PathfindingRequest,
    AlgorithmMetrics,
)
from app.services.pathfinding.engine import run_pathfinding, run_multi_pathfinding
from app.services.graph.graph_service import graph_service


router = APIRouter(prefix="/api/pathfinding", tags=["pathfinding"])


@router.post("/find-path")
async def find_path(request: PathfindingRequest) -> dict:
    """
    Find shortest path between two coordinates using specified algorithm(s).

    Returns results for each algorithm with metrics and path coordinates.
    """
    try:
        center_lat = (request.start.lat + request.end.lat) / 2
        center_lon = (request.start.lon + request.end.lon) / 2

        graph, metadata = await graph_service.get_graph_for_region(
            center_lat, center_lon
        )

        start_node = graph_service.find_nearest_node(
            graph, request.start.lat, request.start.lon
        )
        end_node = graph_service.find_nearest_node(
            graph, request.end.lat, request.end.lon
        )

        if start_node is None or end_node is None:
            raise HTTPException(
                status_code=400,
                detail="Could not find nodes near the specified coordinates",
            )

        if start_node == end_node:
            raise HTTPException(
                status_code=400,
                detail="Start and end resolve to the same node. Try further apart points.",
            )

        results = await run_multi_pathfinding(
            graph,
            start_node,
            end_node,
            request.algorithms,
            request.config,
            websocket=None,
        )

        return {
            "start": request.start.model_dump(),
            "end": request.end.model_dump(),
            "graph_info": metadata,
            "results": [
                {
                    "algorithm": r.algorithm,
                    "path": r.path_coords,
                    "cost": r.cost,
                    "path_length_km": r.path_length_km,
                    "nodes_explored": r.nodes_explored,
                    "computation_time_ms": r.computation_time_ms,
                    "memory_usage_mb": r.memory_usage_mb,
                    "success": r.success,
                    "error": r.error,
                    "extra": r.extra,
                }
                for r in results
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/algorithms")
async def list_algorithms() -> dict:
    """List all available pathfinding algorithms with descriptions."""
    return {
        "dijkstra": {
            "name": "Dijkstra",
            "description": "Shortest path for non-negative weights",
            "time_complexity": "O((V + E) log V)",
            "space_complexity": "O(V)",
            "supports_negative_weights": False,
            "supports_all_pairs": False,
            "parameters": [],
        },
        "astar": {
            "name": "A*",
            "description": "Heuristic-guided shortest path (distance/time)",
            "time_complexity": "O((V + E) log V)",
            "space_complexity": "O(V)",
            "supports_negative_weights": False,
            "supports_all_pairs": False,
            "parameters": ["heuristic_type: haversine|manhattan|euclidean|zero"],
        },
        "bidirectional": {
            "name": "Bidirectional Dijkstra",
            "description": "Simultaneous forward/backward search",
            "time_complexity": "O((V + E) log V)",
            "space_complexity": "O(V)",
            "supports_negative_weights": False,
            "supports_all_pairs": False,
            "parameters": [],
        },
        "bellman_ford": {
            "name": "Bellman-Ford",
            "description": "Shortest path supporting negative weights with cycle detection",
            "time_complexity": "O(V * E)",
            "space_complexity": "O(V)",
            "supports_negative_weights": True,
            "supports_all_pairs": False,
            "parameters": [],
        },
        "floyd_warshall": {
            "name": "Floyd-Warshall",
            "description": "All-pairs shortest paths with dynamic programming",
            "time_complexity": "O(V^3)",
            "space_complexity": "O(V^2)",
            "supports_negative_weights": True,
            "supports_all_pairs": True,
            "parameters": [],
        },
        "yens_k_shortest": {
            "name": "Yen's K-Shortest Paths",
            "description": "Find K alternative shortest paths",
            "time_complexity": "O(K * V * (E + V log V))",
            "space_complexity": "O(K * V)",
            "supports_negative_weights": False,
            "supports_all_pairs": False,
            "parameters": ["k: int (1-10, default=5)"],
        },
    }


@router.get("/algorithm/{algorithm_name}")
async def get_algorithm_info(algorithm_name: str) -> dict:
    """Get detailed information about a specific algorithm."""
    algorithms = await list_algorithms()
    if algorithm_name not in algorithms:
        raise HTTPException(
            status_code=404,
            detail=f"Algorithm '{algorithm_name}' not found. Available: {list(algorithms.keys())}",
        )
    return {algorithm_name: algorithms[algorithm_name]}


@router.post("/benchmark")
async def benchmark_algorithms(
    request: PathfindingRequest,
    iterations: int = Query(1, ge=1, le=10),
) -> dict:
    """Benchmark multiple algorithms on the same path."""
    try:
        center_lat = (request.start.lat + request.end.lat) / 2
        center_lon = (request.start.lon + request.end.lon) / 2

        graph, metadata = await graph_service.get_graph_for_region(
            center_lat, center_lon
        )
        start_node = graph_service.find_nearest_node(
            graph, request.start.lat, request.start.lon
        )
        end_node = graph_service.find_nearest_node(
            graph, request.end.lat, request.end.lon
        )

        if start_node is None or end_node is None:
            raise HTTPException(
                status_code=400, detail="Could not find nodes near coordinates"
            )

        benchmarks = {}
        for algo in request.algorithms:
            runs = []
            for _ in range(iterations):
                result = await run_pathfinding(
                    graph, start_node, end_node, algo, request.config
                )
                runs.append(
                    {
                        "nodes_explored": result.nodes_explored,
                        "computation_time_ms": result.computation_time_ms,
                        "memory_usage_mb": result.memory_usage_mb,
                        "path_length_km": result.path_length_km,
                        "success": result.success,
                    }
                )

            avg_time = sum(r["computation_time_ms"] for r in runs) / len(runs)
            avg_nodes = sum(r["nodes_explored"] for r in runs) / len(runs)
            benchmarks[algo.value] = {
                "iterations": iterations,
                "runs": runs,
                "avg_computation_time_ms": round(avg_time, 2),
                "avg_nodes_explored": round(avg_nodes),
            }

        # Determine best algorithm by avg time
        best = min(benchmarks, key=lambda k: benchmarks[k]["avg_computation_time_ms"])

        return {
            "start": request.start.model_dump(),
            "end": request.end.model_dump(),
            "graph_info": metadata,
            "algorithms_tested": [a.value for a in request.algorithms],
            "iterations": iterations,
            "benchmarks": benchmarks,
            "best_algorithm": best,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare")
async def compare_algorithms(
    lat1: float = Query(..., ge=-90, le=90, description="Start latitude"),
    lon1: float = Query(..., ge=-180, le=180, description="Start longitude"),
    lat2: float = Query(..., ge=-90, le=90, description="End latitude"),
    lon2: float = Query(..., ge=-180, le=180, description="End longitude"),
    algorithms: str = Query(
        "dijkstra,astar,bellman_ford", description="Comma-separated algorithm names"
    ),
) -> dict:
    """Compare multiple algorithms on a single path query."""
    try:
        from app.schemas.pathfinding import Coordinate, PathfindingConfig

        algorithm_list = [a.strip() for a in algorithms.split(",")]
        algo_types = []
        for name in algorithm_list:
            try:
                algo_types.append(AlgorithmType(name))
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Unknown algorithm: {name}"
                )

        center_lat = (lat1 + lat2) / 2
        center_lon = (lon1 + lon2) / 2
        graph, metadata = await graph_service.get_graph_for_region(
            center_lat, center_lon
        )

        start_node = graph_service.find_nearest_node(graph, lat1, lon1)
        end_node = graph_service.find_nearest_node(graph, lat2, lon2)

        if start_node is None or end_node is None:
            raise HTTPException(
                status_code=400, detail="Could not find nodes near coordinates"
            )

        config = PathfindingConfig()
        results = await run_multi_pathfinding(
            graph, start_node, end_node, algo_types, config
        )

        comparison = []
        for r in results:
            comparison.append(
                {
                    "algorithm": r.algorithm,
                    "nodes_explored": r.nodes_explored,
                    "computation_time_ms": r.computation_time_ms,
                    "memory_usage_mb": r.memory_usage_mb,
                    "path_length_km": r.path_length_km,
                    "cost": r.cost,
                    "success": r.success,
                    "error": r.error,
                }
            )

        return {
            "start": {"lat": lat1, "lon": lon1},
            "end": {"lat": lat2, "lon": lon2},
            "graph_info": metadata,
            "algorithms": algorithm_list,
            "comparison": comparison,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
