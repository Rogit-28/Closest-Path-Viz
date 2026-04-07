/** Shared types for the pathfinding visualization platform. */

export type AlgorithmType = 'dijkstra' | 'astar' | 'bidirectional' | 'bellman_ford' | 'floyd_warshall' | 'yens_k_shortest';
export type HeuristicType = 'haversine' | 'manhattan' | 'euclidean' | 'zero';
export type WeightFunction = 'distance' | 'time' | 'hybrid';
export type AnimationGranularity = 'every_node' | 'every_n' | 'frontier_only';

export interface Coordinate {
  lat: number;
  lon: number;
}

export interface HybridWeights {
  alpha: number;
  beta: number;
}

export interface PathfindingConfig {
  astar_heuristic: HeuristicType;
  weight_function: WeightFunction;
  hybrid_weights?: HybridWeights;
  k_paths: number;
  animation_speed: number;
  show_all_explored: boolean;
  animation_granularity: AnimationGranularity;
  floyd_warshall_node_limit?: number; // 1000-5000
}

export interface PathfindingRequest {
  start: Coordinate;
  end: Coordinate;
  algorithms: AlgorithmType[];
  config: PathfindingConfig;
}

export interface NodeCoord {
  node_id: string;
  lat: number;
  lon: number;
}

export interface AlgorithmResult {
  algorithm: string;
  requested_algorithm: string;
  executed_algorithm: string;
  path: NodeCoord[];
  path_geometry?: number[][];
  cost: number | null;
  path_length_km: number;
  nodes_explored: number;
  computation_time_ms: number;
  memory_usage_mb: number;
  success: boolean;
  error: string | null;
  extra: Record<string, unknown>;
}

export interface AlgorithmMetrics {
  algorithm?: string;
  nodes_explored: number;
  path_length_km: number;
  computation_time_ms: number;
  memory_usage_mb: number;
  cost: number | null;
  path_node_count: number;
  extra: Record<string, unknown>;
}

// WebSocket message types
export interface WsNodeVisit {
  type: 'node_visit';
  algorithm: string;
  node_id: string;
  lat: number;
  lon: number;
  cost: number;
  nodes_explored: number;
  metadata: Record<string, unknown>;
}

export interface WsEdgeExplore {
  type: 'edge_explore';
  algorithm: string;
  from_node_id: string;
  to_node_id: string;
  from_lat: number;
  from_lon: number;
  to_lat: number;
  to_lon: number;
  cost: number;
  nodes_explored: number;
  geometry?: number[][];
  metadata: Record<string, unknown>;
}

export interface WsFrontierUpdate {
  type: 'frontier_update';
  algorithm: string;
  frontier_size: number;
  nodes_explored: number;
}

export interface WsComplete {
  type: 'complete';
  algorithm: string;
  requested_algorithm: string;
  executed_algorithm: string;
  path: NodeCoord[];
  path_geometry?: number[][];
  metrics: AlgorithmMetrics;
  success: boolean;
  error: string | null;
}

export interface WsGraphInfo {
  type: 'graph_info';
  metadata: {
    node_count: number;
    edge_count: number;
    fallback_speed_pct: number;
    source: string;
  };
}

export interface WsAlgorithmStart {
  type: 'algorithm_start';
  algorithm: string;
}

export interface WsAllComplete {
  type: 'all_complete';
}

export interface WsWarning {
  type: 'warning';
  algorithm?: string;
  message: string;
}

export type WsMessage =
  | WsNodeVisit
  | WsEdgeExplore
  | WsFrontierUpdate
  | WsComplete
  | WsGraphInfo
  | WsAlgorithmStart
  | WsAllComplete
  | WsWarning
  | { type: 'error'; message: string }
  | { type: 'loading'; message: string };

// Constants for UI
export const ALGORITHM_COLORS: Record<string, string> = {
  dijkstra: '#FF6B6B',
  astar: '#4ECDC4',
  bidirectional: '#45B7D1',
  bellman_ford: '#FFA07A',
  floyd_warshall: '#98D8C8',
  yens_k_shortest: '#DDA0DD',
};

export const ALGORITHM_NAMES: Record<AlgorithmType, string> = {
  dijkstra: 'Dijkstra',
  astar: 'A*',
  bidirectional: 'Bidirectional',
  bellman_ford: 'Bellman-Ford',
  floyd_warshall: 'Floyd-Warshall',
  yens_k_shortest: "Yen's K-Shortest",
};

// User settings — mirrors backend UserSettingsSchema
export interface UserSettingsPathfinding {
  default_algorithm: AlgorithmType;
  astar_heuristic: HeuristicType;
  weight_function: WeightFunction;
  k_paths: number;
  show_all_explored: boolean;
  floyd_warshall_node_limit?: number;
}

export interface UserSettingsVisualization {
  animation_speed: number;
  animation_granularity: AnimationGranularity;
  color_scheme: string;
}

export interface UserSettingsCache {
  refresh_schedule: string;
  prompt_on_refresh: boolean;
  auto_approve_after_days: number;
  defer_max_days: number;
}

export interface UserSettings {
  pathfinding: UserSettingsPathfinding;
  visualization: UserSettingsVisualization;
  cache: UserSettingsCache;
}

// Cached city info — mirrors backend CachedCityResponse
export interface CachedCity {
  id: number;
  name: string;
  country: string;
  lat: number;
  lon: number;
  schedule: string;
  last_refresh: string | null;
  next_refresh: string | null;
  pending_approval: boolean;
  node_count: number;
  edge_count: number;
}

// Additional constants
export const SPEED_OPTIONS = [0.25, 0.5, 1, 2, 5, 10, 50, 0] as const; // 0 = instant
