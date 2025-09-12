"""
FastAPI application entry point.
Pathfinding Visualization Platform — real-time algorithm comparison on road networks.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uuid

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.pathfinding import router as pathfinding_router
from app.api.routes.cache import router as cache_router
from app.api.routes.settings import router as settings_router
from app.websockets import pathfinding_websocket_handler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pathfinding")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    logger.info("Starting Pathfinding Visualization Platform...")

    # Initialize database (optional — graceful if unavailable)
    try:
        from app.core.database import init_db

        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init skipped (not available): {e}")

    # Initialize Redis (optional)
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection skipped (not available): {e}")

    # Create graph cache directory
    Path(settings.GRAPH_CACHE_DIR).mkdir(parents=True, exist_ok=True)

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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(pathfinding_router)
    app.include_router(cache_router)
    app.include_router(settings_router)

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
            "mapbox_token": settings.MAPBOX_TOKEN or "",
            "ws_url": f"ws://localhost:{settings.PORT}/api/pathfinding/ws",
            "floyd_warshall_node_limit": settings.FLOYD_WARSHALL_NODE_LIMIT,
            "fallback_warning_threshold": settings.FALLBACK_SPEED_WARNING_THRESHOLD,
        }

    @app.websocket("/ws/pathfinding")
    async def websocket_endpoint(websocket: WebSocket):
        client_id = str(uuid.uuid4())
        await pathfinding_websocket_handler(websocket, client_id)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
