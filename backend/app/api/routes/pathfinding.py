"""
Pathfinding API endpoints.

Provides REST endpoints for computing shortest paths using various algorithms.
Real-time node visitation is streamed via WebSocket if connected.
"""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.pathfinding import (
    AlgorithmType,
    PathfindingRequest,
)
from app.services.pathfinding.engine import run_pathfinding, run_multi_pathfinding
from app.services.graph.graph_service import graph_service
from app.services.pathfinding.serialization import (
    finite_or_none,
    sanitize_for_json,
    serialize_result_payload,
)


router = APIRouter(prefix="/api/pathfinding", tags=["pathfinding"])


def _resolve_start_end_or_zero(
    graph,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
):
    start_node = graph_service.find_nearest_node(graph, start_lat, start_lon)
    end_node = graph_service.find_nearest_node(graph, end_lat, end_lon)
    if start_node is None or end_node is None:
        raise HTTPException(
            status_code=400,
            detail="Could not find nodes near the specified coordinates",
        )
    return start_node, end_node


def _build_zero_path_result(
    algorithm: str, start_node: str, start_lat: float, start_lon: float
) -> dict:
    return {
        "algorithm": algorithm,
        "requested_algorithm": algorithm,
        "executed_algorithm": algorithm,
        "path": [{"node_id": start_node, "lat": start_lat, "lon": start_lon}],
        "path_geometry": [],
        "cost": 0.0,
        "path_length_km": 0.0,
        "nodes_explored": 1,
        "computation_time_ms": 0.0,
        "memory_usage_mb": 0.0,
        "success": True,
        "error": None,
        "extra": {
            "reason": "start_equals_end",
            "requested_algorithm": algorithm,
            "executed_algorithm": algorithm,
        },
    }


def _build_failed_path_result(
    algorithm: str, error: str, *, executed_algorithm: str | None = None
) -> dict:
    executed = executed_algorithm or algorithm
    return {
        "algorithm": algorithm,
        "requested_algorithm": algorithm,
        "executed_algorithm": executed,
        "path": [],
        "path_geometry": [],
        "cost": None,
        "path_length_km": 0.0,
        "nodes_explored": 0,
        "computation_time_ms": 0.0,
        "memory_usage_mb": 0.0,
        "success": False,
        "error": error,
        "extra": {
            "reason": "execution_failed",
            "requested_algorithm": algorithm,
            "executed_algorithm": executed,
        },
    }


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

        start_node, end_node = _resolve_start_end_or_zero(
            graph,
            request.start.lat,
            request.start.lon,
            request.end.lat,
            request.end.lon,
        )

        if start_node == end_node:
            return {
                "start": request.start.model_dump(),
                "end": request.end.model_dump(),
                "graph_info": metadata,
                "warnings": [
                    "Start and end resolve to same node; returning zero-cost path."
                ],
                "results": [
                    _build_zero_path_result(
                        algo.value, start_node, request.start.lat, request.start.lon
                    )
                    for algo in request.algorithms
                ],
            }

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
                    "algorithm": payload["algorithm"],
                    "requested_algorithm": payload["requested_algorithm"],
                    "executed_algorithm": payload["executed_algorithm"],
                    "path": payload["path"],
                    "path_geometry": payload["path_geometry"],
                    "cost": payload["metrics"]["cost"],
                    "path_length_km": payload["metrics"]["path_length_km"],
                    "nodes_explored": payload["metrics"]["nodes_explored"],
                    "computation_time_ms": payload["metrics"]["computation_time_ms"],
                    "memory_usage_mb": payload["metrics"]["memory_usage_mb"],
                    "success": payload["success"],
                    "error": payload["error"],
                    "extra": payload["metrics"]["extra"],
                }
                for payload in (
                    serialize_result_payload(
                        r,
                        requested_algorithm=request.algorithms[i].value,
                        executed_algorithm=r.algorithm,
                    )
                    for i, r in enumerate(results)
                )
            ],
        }

    except HTTPException:
        raise
    except Exception:
        return {
            "start": request.start.model_dump(),
            "end": request.end.model_dump(),
            "graph_info": None,
            "results": [
                _build_failed_path_result(algo.value, "Failed to compute path.")
                for algo in request.algorithms
            ],
            "warnings": ["Pathfinding failed before completion."],
        }


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
        start_node, end_node = _resolve_start_end_or_zero(
            graph,
            request.start.lat,
            request.start.lon,
            request.end.lat,
            request.end.lon,
        )

        if start_node == end_node:
            raise HTTPException(
                status_code=400,
                detail="Benchmark requires distinct start and end nodes.",
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
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to benchmark algorithms.")


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
        from app.schemas.pathfinding import PathfindingConfig

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

        start_node, end_node = _resolve_start_end_or_zero(graph, lat1, lon1, lat2, lon2)

        if start_node == end_node:
            return {
                "start": {"lat": lat1, "lon": lon1},
                "end": {"lat": lat2, "lon": lon2},
                "graph_info": metadata,
                "warnings": [
                    "Start and end resolve to same node; returning zero-cost path."
                ],
                "algorithms": algorithm_list,
                "comparison": [
                    {
                        "algorithm": algo.value,
                        "nodes_explored": 1,
                        "computation_time_ms": 0.0,
                        "memory_usage_mb": 0.0,
                        "path_length_km": 0.0,
                        "cost": 0.0,
                        "success": True,
                        "error": None,
                    }
                    for algo in algo_types
                ],
            }

        config = PathfindingConfig()
        results = await run_multi_pathfinding(
            graph, start_node, end_node, algo_types, config
        )

        comparison = []
        for r in results:
            comparison.append(
                {
                    "requested_algorithm": r.extra.get(
                        "requested_algorithm", r.algorithm
                    )
                    if r.extra
                    else r.algorithm,
                    "executed_algorithm": r.extra.get("executed_algorithm", r.algorithm)
                    if r.extra
                    else r.algorithm,
                    "algorithm": r.extra.get("requested_algorithm", r.algorithm)
                    if r.extra
                    else r.algorithm,
                    "nodes_explored": r.nodes_explored,
                    "computation_time_ms": r.computation_time_ms,
                    "memory_usage_mb": r.memory_usage_mb,
                    "path_length_km": r.path_length_km,
                    "cost": finite_or_none(r.cost),
                    "success": r.success,
                    "error": r.error,
                    "extra": sanitize_for_json(r.extra or {}),
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
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to compare algorithms.")
