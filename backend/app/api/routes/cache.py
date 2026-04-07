"""
Cache management API routes.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.cache.cache_service import cache_manager
from app.services.graph.graph_service import graph_service
from app.schemas.pathfinding import CacheRefreshRequest, CacheScheduleRequest

logger = logging.getLogger("pathfinding.api.cache")
router = APIRouter(prefix="/api/cache", tags=["cache"])


class CacheWarmRequest(BaseModel):
    """Request to warm the cache for a region."""

    lat: float = Field(..., description="Center latitude")
    lon: float = Field(..., description="Center longitude")
    radius_km: float = Field(default=15.0, ge=1.0, le=100.0, description="Radius in km")


class CacheStatusResponse(BaseModel):
    """Response for cache status check."""

    cached: bool
    cache_key: str
    node_count: int | None = None
    edge_count: int | None = None
    source: str | None = None


def _cache_file_path(cache_key: str) -> Path:
    """Resolve cache file path and guard against path traversal."""
    cache_dir = Path(settings.GRAPH_CACHE_DIR).resolve()
    file_path = (cache_dir / f"{cache_key}.json").resolve()
    if cache_dir not in file_path.parents and file_path != cache_dir:
        raise ValueError("Invalid cache key path")
    return file_path


async def _warm_cache_background(lat: float, lon: float, radius_km: float):
    """Background task to fetch and cache graph."""
    try:
        logger.info(f"Background cache warming: ({lat}, {lon}), radius={radius_km}km")
        await graph_service.get_graph_for_region(lat, lon, radius_km)
        logger.info(f"Background cache warming complete: ({lat}, {lon})")
    except Exception:
        logger.exception("Background cache warming failed")


@router.post("/warm", status_code=202)
async def warm_cache(request: CacheWarmRequest, background_tasks: BackgroundTasks):
    """
    Warm the cache for a region. This triggers a background fetch of the graph
    from OSM if not already cached. Returns immediately.
    """
    cache_key = f"{request.lat:.4f}_{request.lon:.4f}_{request.radius_km:.4f}"

    # Check if already cached (in memory or file)
    file_path = _cache_file_path(cache_key)
    if cache_key in graph_service._graph_cache or file_path.exists():
        return {
            "status": "already_cached",
            "cache_key": cache_key,
            "message": "Graph already cached for this region",
        }

    # Schedule background fetch
    background_tasks.add_task(
        _warm_cache_background, request.lat, request.lon, request.radius_km
    )

    return {
        "status": "warming",
        "cache_key": cache_key,
        "message": "Cache warming started in background",
    }


@router.get("/status")
async def get_cache_status(
    lat: float, lon: float, radius_km: float = 15.0
) -> CacheStatusResponse:
    """
    Check if a region is already cached.
    """
    cache_key = f"{lat:.4f}_{lon:.4f}_{radius_km:.4f}"

    # Check in-memory cache
    if cache_key in graph_service._graph_cache:
        metadata = graph_service._graph_metadata.get(cache_key, {})
        return CacheStatusResponse(
            cached=True,
            cache_key=cache_key,
            node_count=metadata.get("node_count"),
            edge_count=metadata.get("edge_count"),
            source=metadata.get("source"),
        )

    # Check file cache
    file_path = _cache_file_path(cache_key)
    if file_path.exists():
        return CacheStatusResponse(
            cached=True,
            cache_key=cache_key,
            node_count=None,  # Would need to load file to get this
            edge_count=None,
            source="file_cache",
        )

    return CacheStatusResponse(
        cached=False,
        cache_key=cache_key,
    )


@router.get("/cities")
async def get_cached_cities():
    """Get list of all cached/available cities."""
    cities = cache_manager.get_cities_list()
    result = []
    for idx, city in enumerate(cities, start=1):
        schedule = cache_manager.get_schedule(city["name"])
        result.append(
            {
                "id": idx,
                "name": city["name"],
                "lat": city["lat"],
                "lon": city["lon"],
                "country": city["country"],
                "schedule": schedule["schedule_type"],
                "last_refresh": schedule.get("last_refresh"),
                "next_refresh": schedule.get("next_refresh"),
                "pending_approval": schedule.get("pending_approval", False),
                "node_count": 0,
                "edge_count": 0,
            }
        )
    return result


@router.post("/refresh")
async def refresh_cache(request: CacheRefreshRequest):
    """Approve or request a cache refresh for a city."""
    cities = cache_manager.get_cities_list()
    city = next((c for i, c in enumerate(cities) if i + 1 == request.city_id), None)

    if not city:
        raise HTTPException(
            status_code=404, detail=f"City not found with id {request.city_id}"
        )

    if request.approve:
        result = cache_manager.approve_refresh(city["name"])
    else:
        result = cache_manager.defer_refresh(city["name"])

    return result


@router.post("/schedule")
async def set_schedule(request: CacheScheduleRequest):
    """Set refresh schedule for a city."""
    cities = cache_manager.get_cities_list()
    city = next((c for i, c in enumerate(cities) if i + 1 == request.city_id), None)

    if not city:
        raise HTTPException(
            status_code=404, detail=f"City not found with id {request.city_id}"
        )

    prompt_on_refresh = request.prompt_behavior.value == "always_ask"

    result = cache_manager.set_schedule(
        city["name"],
        schedule_type=request.schedule.value,
        prompt_on_refresh=prompt_on_refresh,
    )
    return {"city": city["name"], "schedule": result}
