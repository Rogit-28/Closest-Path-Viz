"""
FastAPI application entry point.
Pathfinding Visualization Platform — real-time algorithm comparison on road networks.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.metrics import metrics
from app.api.routes.pathfinding import router as pathfinding_router
from app.api.routes.cache import router as cache_router
from app.api.routes.settings import router as settings_router
from app.api.routes.pathfinding_sse import router as pathfinding_sse_router
from app.api.routes.metrics import router as metrics_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pathfinding")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    startup_start = time.perf_counter()
    logger.info("Starting Pathfinding Visualization Platform...")

    db_ok = False
    redis_ok = False

    # Initialize database (optional — graceful if unavailable)
    try:
        from app.core.database import init_db

        await init_db()
        logger.info("Database initialized")
        db_ok = True
    except Exception as e:
        logger.warning(f"Database init skipped (not available): {e}")

    # Initialize Redis (optional)
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connected")
        redis_ok = True
    except Exception as e:
        logger.warning(f"Redis connection skipped (not available): {e}")

    # Create graph cache directory
    Path(settings.GRAPH_CACHE_DIR).mkdir(parents=True, exist_ok=True)

    # Record startup metrics
    startup_time_ms = (time.perf_counter() - startup_start) * 1000
    metrics.record_startup(startup_time_ms, db_ok=db_ok, redis_ok=redis_ok)
    logger.info(
        f"Startup complete in {startup_time_ms:.2f}ms (DB: {db_ok}, Redis: {redis_ok})"
    )

    yield

    # Shutdown
    try:
        from app.core.redis import close_redis

        await close_redis()
    except Exception:
        pass
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Real-world pathfinding visualization with algorithm comparison on OpenStreetMap road networks",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not settings.DEBUG:
            response.headers["Cache-Control"] = "no-store"
        return response

    # Routes
    app.include_router(pathfinding_router)
    app.include_router(cache_router)
    app.include_router(settings_router)
    app.include_router(pathfinding_sse_router)
    app.include_router(metrics_router)

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "algorithms": [
                "dijkstra",
                "astar",
                "bidirectional",
                "bellman_ford",
                "floyd_warshall",
            ],
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}

    @app.get("/api/config")
    async def get_frontend_config():
        return {
            "sse_url": "/api/pathfinding/stream",
            "floyd_warshall_node_limit": settings.FLOYD_WARSHALL_NODE_LIMIT,
            "fallback_warning_threshold": settings.FALLBACK_SPEED_WARNING_THRESHOLD,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
