"""
Cache management API routes.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.cache.cache_service import cache_manager
from app.schemas.pathfinding import CacheRefreshRequest, CacheScheduleRequest

logger = logging.getLogger("pathfinding.api.cache")
router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/cities")
async def get_cached_cities():
    """Get list of all cached/available cities."""
    cities = cache_manager.get_cities_list()
    result = []
    for city in cities:
        schedule = cache_manager.get_schedule(city["name"])
        result.append(
            {
                "name": city["name"],
                "lat": city["lat"],
                "lon": city["lon"],
                "country": city["country"],
                "schedule": schedule["schedule_type"],
                "last_refresh": schedule.get("last_refresh"),
                "next_refresh": schedule.get("next_refresh"),
                "pending_approval": schedule.get("pending_approval", False),
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

    prompt_on_refresh = request.prompt_behavior == "always_ask"

    result = cache_manager.set_schedule(
        city["name"],
        schedule_type=request.schedule,
        prompt_on_refresh=prompt_on_refresh,
    )
    return {"city": city["name"], "schedule": result}
