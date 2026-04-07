from pydantic import BaseModel, Field
from typing import Optional, Any
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


class AnimationGranularity(str, Enum):
    EVERY_NODE = "every_node"
    EVERY_N = "every_n"
    FRONTIER_ONLY = "frontier_only"


class CacheScheduleType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    MANUAL = "manual"


class CachePromptBehavior(str, Enum):
    ALWAYS_ASK = "always_ask"
    AUTO_APPROVE = "auto_approve"


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
    animation_granularity: AnimationGranularity = AnimationGranularity.EVERY_NODE
    floyd_warshall_node_limit: int = Field(1000, ge=100, le=5000)


class PathfindingRequest(BaseModel):
    start: Coordinate
    end: Coordinate
    algorithms: list[AlgorithmType] = Field(
        default_factory=lambda: [AlgorithmType.ASTAR], min_length=1
    )
    config: PathfindingConfig = Field(default_factory=PathfindingConfig)


class NodeVisitMessage(BaseModel):
    type: str = "node_visit"
    algorithm: str
    node_id: str
    lat: float
    lon: float
    cost: float
    nodes_explored: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class FrontierUpdateMessage(BaseModel):
    type: str = "frontier_update"
    algorithm: str
    frontier_size: int
    nodes_explored: int


class PathCompleteMessage(BaseModel):
    type: str = "complete"
    algorithm: str
    path: list[dict[str, Any]]
    metrics: dict[str, Any]


class AlgorithmMetrics(BaseModel):
    algorithm: str
    nodes_explored: int
    path_length_km: float
    computation_time_ms: float
    memory_usage_mb: float
    path_node_count: int
    extra: dict[str, Any] = Field(default_factory=dict)


class CachedCityResponse(BaseModel):
    id: int
    name: str
    country: str
    lat: float
    lon: float
    schedule: str = "weekly"
    last_refresh: Optional[str] = None
    next_refresh: Optional[str] = None
    pending_approval: bool = False
    node_count: int = 0
    edge_count: int = 0


class CacheRefreshRequest(BaseModel):
    city_id: int = Field(..., ge=1)
    approve: bool = True


class CacheScheduleRequest(BaseModel):
    city_id: int = Field(..., ge=1)
    schedule: CacheScheduleType = CacheScheduleType.WEEKLY
    prompt_behavior: CachePromptBehavior = CachePromptBehavior.ALWAYS_ASK


class UserPathfindingSettings(BaseModel):
    default_algorithm: AlgorithmType = AlgorithmType.ASTAR
    astar_heuristic: HeuristicType = HeuristicType.HAVERSINE
    weight_function: WeightFunction = WeightFunction.DISTANCE
    k_paths: int = Field(1, ge=1, le=10)
    show_all_explored: bool = True
    floyd_warshall_node_limit: int = Field(1000, ge=100, le=5000)


class UserVisualizationSettings(BaseModel):
    animation_speed: float = Field(1.0, ge=0.25, le=50.0)
    animation_granularity: AnimationGranularity = AnimationGranularity.EVERY_NODE
    color_scheme: str = "default"


class UserCacheSettings(BaseModel):
    refresh_schedule: CacheScheduleType = CacheScheduleType.WEEKLY
    prompt_on_refresh: bool = True
    auto_approve_after_days: int = Field(7, ge=1, le=365)
    defer_max_days: int = Field(7, ge=1, le=365)


class UserSettingsSchema(BaseModel):
    pathfinding: UserPathfindingSettings = Field(
        default_factory=UserPathfindingSettings
    )
    visualization: UserVisualizationSettings = Field(
        default_factory=UserVisualizationSettings
    )
    cache: UserCacheSettings = Field(default_factory=UserCacheSettings)


class GraphInfoResponse(BaseModel):
    city_name: str
    node_count: int
    edge_count: int
    bbox: dict[str, float]
    fallback_speed_pct: float
    is_cached: bool
