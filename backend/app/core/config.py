from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Pathfinding Visualization Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/pathfinding"
    )
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@localhost:5432/pathfinding"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 86400  # 24 hours

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # OSM / Graph
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    DEFAULT_GRAPH_RADIUS_KM: float = 10.0
    FLOYD_WARSHALL_NODE_LIMIT: int = 1000
    GRAPH_CACHE_DIR: str = "./data/graphs"

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100

    # Mapbox (passed to frontend)
    MAPBOX_TOKEN: Optional[str] = None

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Speed limit defaults (km/h)
    SPEED_MOTORWAY: int = 100
    SPEED_TRUNK: int = 100
    SPEED_PRIMARY: int = 60
    SPEED_SECONDARY: int = 40
    SPEED_TERTIARY: int = 40
    SPEED_RESIDENTIAL: int = 30
    SPEED_UNCLASSIFIED: int = 20
    SPEED_SERVICE: int = 20
    SPEED_DEFAULT: int = 30

    # Fallback warning threshold
    FALLBACK_SPEED_WARNING_THRESHOLD: float = 0.20  # 20%

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
