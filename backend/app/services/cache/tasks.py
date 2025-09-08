"""
Celery tasks for background cache management.
"""

import logging
from app.core.celery_app import celery_app

logger = logging.getLogger("pathfinding.cache.tasks")


@celery_app.task(name="check_refresh_schedule")
def check_refresh_schedule():
    """Periodic task to check which cities need cache refresh."""
    from app.services.cache.cache_service import cache_manager

    due_cities = cache_manager.get_cities_due_for_refresh()
    for city in due_cities:
        city_name = city["name"]
        if city.get("prompt_on_refresh", True):
            logger.info(f"Cache refresh due for {city_name} — awaiting approval")
            cache_manager.request_refresh(city_name)
        else:
            logger.info(f"Auto-refreshing cache for {city_name}")
            refresh_city_cache.delay(city_name)

    return {"checked": len(due_cities), "cities": [c["name"] for c in due_cities]}


@celery_app.task(name="refresh_city_cache", bind=True, max_retries=3)
def refresh_city_cache(self, city_name: str):
    """Refresh the graph cache for a specific city."""
    import asyncio
    from app.services.graph.graph_service import graph_service
    from app.services.cache.cache_service import cache_manager, TOP_CITIES

    logger.info(f"Starting cache refresh for {city_name}")

    city = next((c for c in TOP_CITIES if c["name"] == city_name), None)
    if not city:
        logger.error(f"City not found: {city_name}")
        return {"error": f"City not found: {city_name}"}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        graph, metadata = loop.run_until_complete(
            graph_service.get_graph_for_region(city["lat"], city["lon"], radius_km=10)
        )
        loop.close()

        cache_manager.approve_refresh(city_name)
        logger.info(f"Cache refreshed for {city_name}: {metadata}")
        return {"city": city_name, "metadata": metadata}
    except Exception as exc:
        logger.error(f"Cache refresh failed for {city_name}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(name="prefetch_top_cities")
def prefetch_top_cities(count: int = 10):
    """Pre-fetch graphs for top N cities."""
    from app.services.cache.cache_service import TOP_CITIES

    results = []
    for city in TOP_CITIES[:count]:
        result = refresh_city_cache.delay(city["name"])
        results.append({"city": city["name"], "task_id": str(result.id)})

    return {"queued": len(results), "tasks": results}
