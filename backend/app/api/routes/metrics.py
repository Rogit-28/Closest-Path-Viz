"""
Metrics API endpoint for performance monitoring.
"""

from fastapi import APIRouter
from app.core.metrics import metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics():
    """
    Get current performance metrics.

    Returns metrics including:
    - Startup time and uptime
    - Graph loading statistics (cache hits/misses, load times)
    - Algorithm performance (per-algorithm stats)
    - SSE connection statistics
    - Request counts
    """
    return metrics.get_metrics()


@router.get("/summary")
async def get_metrics_summary():
    """
    Get a condensed summary of key metrics.
    Useful for quick health checks.
    """
    data = metrics.get_metrics()

    return {
        "uptime_seconds": data["startup"]["uptime_seconds"],
        "startup_time_ms": data["startup"]["time_ms"],
        "graph_cache_hit_rate": data["graph"]["cache_hit_rate_pct"],
        "graph_loads": data["graph"]["loads_total"],
        "sse_active": data["sse"]["active_connections"],
        "requests_active": data["requests"]["active"],
        "algorithms_run": sum(
            algo.get("runs", 0) for algo in data["algorithms"].values()
        ),
    }
