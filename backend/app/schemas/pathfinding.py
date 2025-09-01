from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AlgorithmType(str, Enum):
    DIJKSTRA = "dijkstra"
    ASTAR = "astar"
    BIDIRECTIONAL = "bidirectional"
    BELLMAN_FORD = "bellman_ford"
    FLOYD_WARSHALL = "floyd_warshall"
    YENS_K_SHORTEST = "yens_k_shortest"


class HeuristicType(str, Enum):
    HAVERSINE = "haversine"
    MANHATTAN = "manhattan"
    EUCLIDEAN = "euclidean"
    ZERO = "zero"


class WeightFunction(str, Enum):
    DISTANCE = "distance"
    TIME = "time"
    HYBRID = "hybrid"


class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class HybridWeights(BaseModel):
    alpha: float = Field(0.6, ge=0, le=1, description="Distance weight")
    beta: float = Field(0.4, ge=0, le=1, description="Time weight")


class PathfindingConfig(BaseModel):
    astar_heuristic: HeuristicType = HeuristicType.HAVERSINE
    weight_function: WeightFunction = WeightFunction.DISTANCE
    hybrid_weights: Optional[HybridWeights] = None
    k_paths: int = Field(1, ge=1, le=10)
    animation_speed: float = Field(1.0, ge=0.25, le=50.0)
    show_all_explored: bool = True
    animation_granularity: str = "every_node"  # every_node, every_n, frontier_only


class PathfindingRequest(BaseModel):
    start: Coordinate
    end: Coordinate
    algorithms: list[AlgorithmType] = [AlgorithmType.ASTAR]
    config: PathfindingConfig = PathfindingConfig()


class NodeVisitMessage(BaseModel):
    type: str = "node_visit"
    algorithm: str
    node_id: str
    lat: float
    lon: float
    cost: float
    nodes_explored: int
    metadata: dict = {}


class FrontierUpdateMessage(BaseModel):
    type: str = "frontier_update"
    algorithm: str
    frontier_size: int
    nodes_explored: int


class PathCompleteMessage(BaseModel):
    type: str = "complete"
    algorithm: str
    path: list[dict]
    metrics: dict


class AlgorithmMetrics(BaseModel):
    algorithm: str
    nodes_explored: int
    path_length_km: float
    computation_time_ms: float
    memory_usage_mb: float
    path_node_count: int
    extra: dict = {}


class CachedCityResponse(BaseModel):
    id: int
    name: str
    last_updated: Optional[str] = None
    next_refresh: Optional[str] = None
    refresh_schedule: str = "weekly"
    pending_approval: bool = False
    node_count: int = 0
    edge_count: int = 0


class CacheRefreshRequest(BaseModel):
    city_id: int
    approve: bool = True


class CacheScheduleRequest(BaseModel):
    city_id: int
    schedule: str = "weekly"
    prompt_behavior: str = "always_ask"


class UserSettingsSchema(BaseModel):
    pathfinding: dict = {
        "default_algorithm": "astar",
        "astar_heuristic": "haversine",
        "weight_function": "distance",
        "k_paths": 1,
        "show_all_explored": True,
    }
    visualization: dict = {
        "animation_speed": 1.0,
        "animation_granularity": "every_node",
        "color_scheme": "default",
    }
    cache: dict = {
        "refresh_schedule": "weekly",
        "prompt_on_refresh": True,
        "auto_approve_after_days": 7,
        "defer_max_days": 7,
    }


class GraphInfoResponse(BaseModel):
    city_name: str
    node_count: int
    edge_count: int
    bbox: dict
    fallback_speed_pct: float
    is_cached: bool
