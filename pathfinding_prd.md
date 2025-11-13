# PRD: Real-World Pathfinding Visualization Platform

## 1. Overview
Interactive web application demonstrating shortest path algorithms (A*, Dijkstra, Bidirectional Dijkstra, Bellman-Ford, Floyd-Warshall) on real-world maps with animated node exploration visualization.

## 2. Core Objectives
- Visualize pathfinding algorithms on actual road networks via OpenStreetMap
- Real-time animated node-by-node exploration rendering
- Comparative algorithm performance analytics
- Scalable architecture supporting city-to-country level routing
- User-configurable algorithm parameters and visualization settings

## 3. Technical Architecture

### 3.1 Microservices Design

**Service 1: Graph Data Service (Python/FastAPI)**
- OSM data extraction via Overpass API + `osmnx`
- Graph construction (intersections as nodes, road segments as weighted edges)
- PostgreSQL + PostGIS for spatial data storage
- Redis for graph caching layer

**Service 2: Pathfinding Engine (Python/FastAPI)**
- Algorithm implementations: A*, Dijkstra, Bidirectional Dijkstra, Bellman-Ford, Floyd-Warshall
- Real-time node visit streaming via WebSocket
- Performance metrics collection (nodes explored, path cost)
- K-shortest paths computation

**Service 3: Cache Management Service (Python/Celery)**
- Pre-fetches top 100 cities by population + urban area
- User-configurable refresh schedules
- Prompt-based re-fetch approval flow
- Atomic cache replacement (delete old → fetch new)

**Service 4: Frontend (React + TypeScript)**
- Mapbox GL JS for map rendering
- WebSocket client for animation state
- Algorithm comparison UI with side-by-side metrics
- User settings panel for algorithm parameters

### 3.2 Data Flow
1. User selects start/end coordinates on map
2. User configures: algorithm(s), heuristic type, weight function, animation speed, path count
3. Frontend → Pathfinding Engine: Request with configuration
4. Engine checks Graph Data Service for cached region
5. If cached: Immediate pathfinding execution
6. If not cached: On-demand OSM fetch + graph build
7. Engine streams node visits via WebSocket → Frontend renders animation
8. Final path(s) + metrics returned on completion

## 4. Key Features

### 4.1 Graph Construction [COMPLETED]
- **Files:**
  - `services/graph-data-service/app/core/graph.py`
  - `services/graph-data-service/app/db/models.py`
  - `services/graph-data-service/app/db/crud.py`
  - `services/graph-data-service/app/api/endpoints.py`
- **Node Definition:** Road intersections, dead ends, POIs
- **Edge Weights:** User-selectable
  - Distance (meters): Haversine calculation
  - Time (seconds): Distance ÷ speed limit from OSM road type with fallback strategy
  - Custom: User-uploaded weight matrix
- **Graph Format:** NetworkX DiGraph serialized to adjacency list

**Time-based Weight Fallback Strategy:**
When speed limit or road type data is unavailable:
1. Check OSM `maxspeed` tag → Use if present
2. Check OSM `highway` tag → Map to default speed:
   - motorway/trunk: 100 km/h
   - primary: 60 km/h
   - secondary/tertiary: 40 km/h
   - residential: 30 km/h
   - unclassified/service: 20 km/h
3. If both missing → Use regional default (configurable per country, default: 30 km/h)
4. Log missing data percentage per graph for user transparency
5. UI warning badge: "X% edges using fallback speeds" when threshold >20%

**Floyd-Warshall Computational Complexity:**
- Time: O(n³) where n = node count
- Space: O(n²) distance matrix storage
- For 1000 nodes: ~1 billion operations, ~8MB memory (acceptable)
- For 10,000 nodes: ~1 trillion operations, ~800MB memory (prohibitive)
- For 100,000 nodes: ~1 quadrillion operations, ~80GB memory (impossible)

**Floyd-Warshall Limitations:**
- Disabled in UI when graph exceeds user-configured threshold (default: 1000 nodes)
- Alternative: Pre-compute for small neighborhoods/districts only
- Use case: "Find shortest paths between all landmarks in downtown area" vs full city routing

### 4.2 Algorithm Implementations

**Single-Source Shortest Path:**
- **Dijkstra:** Standard priority queue implementation
- **Bidirectional Dijkstra:** Simultaneous forward/backward search
- **A*:** Priority queue with heuristic function
- **Bellman-Ford:** Handles negative weights, edge relaxation

**All-Pairs Shortest Path:**
- **Floyd-Warshall:** Dynamic programming approach (limited to small subgraphs <1000 nodes)

**Multiple Paths:**
- **Yen's K-Shortest Paths:** Top-K alternative routes

### 4.3 User-Configurable Parameters

**Algorithm Selection:**
- Single algorithm execution
- Multi-algorithm comparison (side-by-side or sequential)
- All algorithms benchmark mode

**A* Heuristic Options:**
- Haversine distance (great-circle)
- Manhattan distance (L1 norm)
- Euclidean distance (L2 norm)
- Zero heuristic (degrades to Dijkstra)

**Edge Weight Function:**
- Distance-based (default)
- Time-based (requires speed limit data)
- Hybrid (weighted combination: α×distance + β×time)

**Animation Settings:**
- Speed: 0.25x, 0.5x, 1x, 2x, 5x, 10x, 50x, Instant
- Granularity: Every node | Every N nodes | Frontier updates only
- Pause/Resume/Step-forward controls

**Path Options:**
- Single optimal path
- Top-K paths (K = 1-10)
- Show all explored nodes vs path-only

**Refresh Schedule (Cache Management):**
- Daily, Weekly, Bi-weekly, Monthly
- Manual only
- Prompt behavior: Always ask | Auto-approve after 7 days

### 4.4 Pathfinding Visualization
- **Visual States:**
  - Unexplored nodes: Gray
  - Frontier nodes: Orange glow
  - Explored nodes: Yellow pulse
  - Final path: Bold blue line (primary), lighter blues for alternatives
  - Start/End: Green/Red markers
  - Current node: Red pulsing ring

### 4.5 Metrics Dashboard
**Real-time (during execution):**
- Nodes explored counter
- Current frontier size
- Elapsed computation time
- Current best path cost

**Post-execution per algorithm:**
- Total nodes explored
- Final path length (km)
- Computation time (ms)
- Memory usage (MB)
- Algorithm-specific:
  - A*: Heuristic effectiveness ratio (h(n) / actual cost)
  - Bidirectional: Meeting point node
  - Bellman-Ford: Negative cycle detection status
  - K-shortest: Paths overlap percentage

**Comparison View (multi-algorithm):**
- Side-by-side metrics table
- Speedup factors
- Node exploration efficiency (path length / nodes explored)
- Visual overlay: Different color per algorithm's explored region

### 4.6 Cache Management
- Background Celery worker checks refresh schedule
- On trigger: Notification to user (in-app banner + optional email)
- User approval/defer options (defer max: user-configurable, default 7 days)
- On approval: Transaction-wrapped cache replacement
  ```
  BEGIN TRANSACTION
  DELETE FROM cached_graphs WHERE city_id = X
  INSERT INTO cached_graphs (OSM fetch + graph build)
  UPDATE cache_metadata SET last_refresh = NOW()
  COMMIT
  ```

## 5. Implementation Details

### 5.1 Tech Stack
**Backend:**
- Python 3.11+
- FastAPI (API gateway + services)
- Celery + Redis (async tasks + cache)
- PostgreSQL 15 + PostGIS (spatial storage)
- `osmnx` (OSM → NetworkX graph)
- `networkx` (graph algorithms)
- WebSockets (real-time streaming)
- `heapq` (priority queues)
- `numpy` (matrix operations for Floyd-Warshall)

**Frontend:**
- React 18 + TypeScript
- Mapbox GL JS (map rendering)
- WebSocket client (native WebSocket API)
- Recharts (metrics visualization)
- Tailwind CSS (styling)
- Zustand (state management)

### 5.2 Critical Code Components

**Generic Pathfinding Interface:**
```python
class PathfindingAlgorithm(ABC):
    @abstractmethod
    async def find_path(self, graph, start, end, websocket, config):
        pass
    
    async def stream_node_visit(self, websocket, node_id, cost, metadata):
        await websocket.send_json({
            "type": "node_visit",
            "node": node_id,
            "cost": cost,
            "metadata": metadata
        })
```

**A* with Configurable Heuristic:**
```python
class AStarPathfinder(PathfindingAlgorithm):
    def __init__(self, heuristic_type: str):
        self.heuristic = {
            "haversine": self._haversine,
            "manhattan": self._manhattan,
            "euclidean": self._euclidean,
            "zero": lambda a, b: 0
        }[heuristic_type]
    
    async def find_path(self, graph, start, end, websocket, config):
        # Standard A* with streaming
```

**K-Shortest Paths (Yen's Algorithm):**
```python
async def yens_k_shortest(graph, start, end, k, websocket):
    A = [await dijkstra(graph, start, end, websocket)]
    B = []
    
    for k_iter in range(1, k):
        for i in range(len(A[-1]) - 1):
            spur_node = A[-1][i]
            root_path = A[-1][:i+1]
            # ... Yen's logic with streaming
```

**Cache Refresh Scheduler:**
```python
@celery.task
def check_refresh_schedule():
    cities = get_cities_due_for_refresh()
    for city in cities:
        user_prefs = get_user_preferences(city.user_id)
        
        if user_prefs.prompt_on_refresh:
            send_refresh_prompt(city)
        elif user_prefs.auto_approve:
            refresh_city_cache.delay(city.id)

@celery.task
def refresh_city_cache(city_id):
    with transaction.atomic():
        CachedGraph.objects.filter(city_id=city_id).delete()
        new_graph = fetch_osm_and_build_graph(city_id)
        CachedGraph.objects.create(
            city_id=city_id,
            data=new_graph,
            last_updated=timezone.now()
        )
```

### 5.3 OSM Data Strategy
**Top 100 Cities Pre-fetch:**
- Source: UN World Urbanization Prospects 2024
- Bounding boxes from city administrative boundaries
- Estimated storage: 5-20GB total (50-200MB per city)
- Initial fetch: Parallel Celery tasks

**On-demand Fetching:**
- Calculate bounding box: 10km radius from start/end midpoint
- Overpass API query with road network filter
- Graph build + ephemeral cache (24 hours)

### 5.4 Scalability Considerations
**City-level (v1):** ~10K nodes
- In-memory graph operations
- All algorithms supported

**State-level (v1):** ~100K nodes
- Floyd-Warshall disabled (too memory intensive)
- Graph partitioning for Bellman-Ford
- Load balanced services

**Country-level (v2):** ~1M+ nodes
- Requires hierarchical routing
- Pre-computed shortcuts
- Distributed caching

## 6. API Specifications

### 6.1 Pathfinding Endpoint
```
POST /api/pathfinding/route
{
  "start": {"lat": 40.7128, "lon": -74.0060},
  "end": {"lat": 40.7580, "lon": -73.9855},
  "algorithms": ["astar", "dijkstra", "bidirectional"],
  "config": {
    "astar_heuristic": "haversine" | "manhattan" | "euclidean" | "zero",
    "weight_function": "distance" | "time" | "hybrid",
    "hybrid_weights": {"alpha": 0.6, "beta": 0.4},
    "k_paths": 3,
    "animation_speed": 1.0
  }
}

WebSocket stream:
{"type": "node_visit", "algorithm": "astar", "node_id": "123", "cost": 450.2}
{"type": "frontier_update", "algorithm": "dijkstra", "frontier_size": 45}
{"type": "complete", "algorithm": "astar", "path": [...], "metrics": {...}}
```

### 6.2 Settings Management
```
GET /api/user/settings
Response: {
  "cache_refresh_schedule": "weekly",
  "prompt_on_refresh": true,
  "default_algorithm": "astar",
  "default_heuristic": "haversine",
  "animation_speed": 1.0
}

PUT /api/user/settings
{
  "cache_refresh_schedule": "daily" | "weekly" | "biweekly" | "monthly" | "manual",
  "prompt_on_refresh": boolean,
  "auto_approve_after_days": number
}
```

### 6.3 Cache Management
```
GET /api/cache/cities
Response: [
  {
    "id": 1,
    "name": "New York",
    "last_updated": "2025-01-15",
    "next_refresh": "2025-02-15",
    "refresh_schedule": "monthly",
    "pending_approval": false
  }
]

POST /api/cache/refresh
{
  "city_id": 1,
  "approve": true
}

POST /api/cache/schedule
{
  "city_id": 1,
  "schedule": "weekly",
  "prompt_behavior": "always_ask" | "auto_approve"
}
```

## 7. Success Metrics
- **Performance:** Sub-100ms pathfinding for city-level routes
- **Accuracy:** Paths within 5% of optimal solution
- **UX:** Sub-1s latency from click to animation start (cached regions)
- **Scalability:** Support 100 concurrent users per service instance

## 8. Implementation Plan

### Core Infrastructure
- Microservices scaffolding (FastAPI + React)
- PostgreSQL + PostGIS + Redis setup
- OSM Overpass API integration
- Graph extraction pipeline (`osmnx` → NetworkX)
- Basic map rendering (Mapbox GL JS)

### Pathfinding Engine
- Algorithm abstract base class
- WebSocket streaming infrastructure
- Dijkstra implementation
- A* with configurable heuristics (Haversine, Manhattan, Euclidean, Zero)
- Bidirectional Dijkstra
- Bellman-Ford with negative cycle detection
- Floyd-Warshall with node threshold limiter
- Yen's K-shortest paths
- Weight function handlers (distance, time with fallbacks, hybrid)

### Visualization Layer
- Real-time node visit rendering
- Animation state management
- Multi-algorithm side-by-side view
- Animation controls (play/pause/speed/step)
- Path overlay rendering (primary + alternatives)
- Visual state differentiation (unexplored/frontier/explored/path)

### Metrics & Analytics
- Real-time performance counters
- Post-execution statistics dashboard
- Algorithm comparison tables
- Heuristic effectiveness analysis
- Memory usage tracking
- Metrics export (CSV/JSON)

### User Configuration
- Settings management API
- Frontend settings panel
- Default preferences persistence
- Per-query parameter overrides
- Algorithm selection interface
- Heuristic/weight/animation controls

### Cache Management
- Top 100 cities identification & pre-fetch
- On-demand graph fetching for uncached regions
- Celery background workers
- Refresh scheduling system
- User approval workflow (prompt/defer/approve)
- Atomic cache replacement transactions
- Cache staleness monitoring

### Data Quality & Reliability
- Speed limit fallback hierarchy
- Missing data logging & reporting
- UI warning system for data quality issues
- Error handling for OSM API failures
- Graph validation (connectivity, weight sanity checks)
- Graceful degradation strategies

### Testing & Validation
- Unit tests for each algorithm
- Integration tests for service communication
- WebSocket connection stability tests
- Performance benchmarks (city/state scale)
- Edge case validation (no path, same start/end, negative cycles)
- Cross-browser compatibility

### Documentation & Deployment
- API documentation (OpenAPI/Swagger)
- User guide for algorithm selection
- Deployment configurations (Docker Compose)
- Monitoring & logging setup
- Database migration scripts
- CI/CD pipeline

## 9. User Settings Schema
```json
{
  "pathfinding": {
    "default_algorithm": "astar",
    "astar_heuristic": "haversine",
    "weight_function": "distance",
    "k_paths": 1,
    "show_all_explored": true
  },
  "visualization": {
    "animation_speed": 1.0,
    "animation_granularity": "every_node",
    "color_scheme": "default"
  },
  "cache": {
    "refresh_schedule": "weekly",
    "prompt_on_refresh": true,
    "auto_approve_after_days": 7,
    "defer_max_days": 7
  }
}
```

## 10. Edge Cases & Validation
- **No path exists:** Return empty path with notification
- **Start = End:** Return zero-cost path immediately
- **Invalid coordinates:** Return 400 with error message
- **Graph too large for Floyd-Warshall:** Disable algorithm option in UI
- **Negative weight cycles (Bellman-Ford):** Flag and warn user
- **OSM API timeout:** Fall back to cached nearest region or return 503
- **K-shortest with K > possible paths:** Return all available paths