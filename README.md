# Pathfinding Visualization Platform

Local-first pathfinding algorithm visualization on OpenStreetMap road networks.
Compare Dijkstra, A*, Bidirectional Search, Bellman-Ford, and Floyd-Warshall with real-time streamed exploration events, interactive map playback controls, and metrics.

![Tech Stack](https://img.shields.io/badge/React_18-TypeScript-blue) ![Backend](https://img.shields.io/badge/FastAPI-Python-green) ![Map](https://img.shields.io/badge/MapLibre_GL_JS-purple)

## Highlights

- **5 core pathfinding algorithms** with side-by-side comparison
- **SSE streaming pipeline** (`/api/pathfinding/stream`) for real-time exploration events
- **Client-side playback engine** (pause/resume/scrub/speed control) via Zustand + `requestAnimationFrame`
- **Interactive MapLibre map** with start/end point selection and rendered path geometry
- **Configurable routing** (A* heuristics, distance/time/hybrid weights, K-path behavior)
- **Cache APIs** for graph warming and status checks (`/api/cache/warm`, `/api/cache/status`)
- **Metrics APIs** (`/metrics`, `/metrics/summary`) for runtime performance and connection stats
- **Graceful local fallback** to synthetic graph when OSM data is unavailable

## Local-First Runtime Model

This project is intended to run **locally** and degrades gracefully when optional services are missing.

- PostgreSQL and Redis are optional for development/runtime startup
- If OSM ingestion fails, backend serves a synthetic fallback graph
- Frontend and backend run independently (`5173` + `8000`) during local development
- Docker Compose can run the full local stack when you want all services together

## Architecture (Current)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Frontend (React 18 + TypeScript + Vite)                                │
│ ├── MapLibre GL JS: map + path/exploration layers                      │
│ ├── Zustand appStore: global app/run/results state                     │
│ ├── Zustand playbackStore: event buffering + playback indices/speed    │
│ ├── useSSEPathfinding: EventSource client for /api/pathfinding/stream  │
│ └── usePlaybackLoop: requestAnimationFrame playback engine             │
├─────────────────────────────────────────────────────────────────────────┤
│ Backend (FastAPI + Python)                                              │
│ ├── /api/pathfinding/stream: SSE event stream                           │
│ ├── /api/pathfinding/*: REST endpoints (find-path, compare, benchmark) │
│ ├── Pathfinding engine: dijkstra, astar, bidirectional, bellman_ford,  │
│ │   floyd_warshall (+ yen_k_shortest support path)                      │
│ ├── Graph service: OSM fetch + in-memory/file cache + synthetic fallback│
│ ├── Cache routes: warm/status/cities/refresh/schedule                  │
│ └── Metrics routes: runtime/graph/algorithm/SSE stats                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Local Infrastructure                                                     │
│ ├── Optional PostgreSQL + PostGIS                                       │
│ ├── Optional Redis                                                      │
│ ├── Docker Compose orchestration                                        │
│ └── Optional Nginx static + reverse proxy setup                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker + Docker Compose (optional)

### 1) Run Backend (local)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend endpoints:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 2) Run Frontend (local)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

### 3) Optional: Full local stack with Docker

```bash
docker compose up --build
```

This brings up postgres, redis, backend, and nginx as local services.

## Configuration

### Backend

Copy `backend/.env.example` to `backend/.env` and adjust if needed.

Important settings:

```env
DATABASE_URL=postgresql+asyncpg://pathfinder:pathfinder_password@localhost:5432/pathfinding
REDIS_URL=redis://localhost:6379/0
DEFAULT_GRAPH_RADIUS_KM=10.0
FLOYD_WARSHALL_NODE_LIMIT=1000
GRAPH_CACHE_DIR=./data/graphs
```

### Frontend

`frontend/.env.example` includes:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

Current runtime pathfinding stream is SSE-based (`/api/pathfinding/stream`).

## API Surface (Current)

### Core + Streaming

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/pathfinding/stream` | SSE stream for visualization events (`loading`, `node_visit`, `edge_explore`, `frontier_update`, `algorithm_start`, `complete`, `all_complete`, etc.) |
| `POST` | `/api/pathfinding/find-path` | Non-streaming pathfinding run |
| `GET` | `/api/pathfinding/algorithms` | List supported algorithms |
| `GET` | `/api/pathfinding/algorithm/{algorithm_name}` | Get metadata for one algorithm |
| `POST` | `/api/pathfinding/benchmark` | Benchmark selected algorithms |
| `GET` | `/api/pathfinding/compare` | Compare algorithms for one coordinate pair |

### Cache + Settings + Metrics

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/cache/warm` | Warm region graph cache in background |
| `GET` | `/api/cache/status` | Check cache presence for region |
| `GET` | `/api/cache/cities` | List configured cached cities |
| `POST` | `/api/cache/refresh` | Approve/defer city refresh |
| `POST` | `/api/cache/schedule` | Set city refresh schedule |
| `GET` | `/api/user/settings` | Read user settings |
| `PUT` | `/api/user/settings` | Update user settings |
| `DELETE` | `/api/user/settings` | Reset user settings |
| `GET` | `/metrics` | Full runtime metrics |
| `GET` | `/metrics/summary` | Condensed health/usage summary |
| `GET` | `/api/config` | Frontend runtime config (includes `sse_url`) |
| `GET` | `/health` | Health check |

## Algorithms

| Algorithm | Time Complexity | Space | Best For |
|---|---|---|---|
| **Dijkstra** | O((V+E) log V) | O(V) | Guaranteed shortest path with non-negative weights |
| **A*** | O((V+E) log V) | O(V) | Faster targeted search with heuristics |
| **Bidirectional Dijkstra** | O((V+E) log V) | O(V) | Reduced search space from both ends |
| **Bellman-Ford** | O(V·E) | O(V) | Supports negative weights |
| **Floyd-Warshall** | O(V³) | O(V²) | All-pairs shortest paths |

## Project Structure

```
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.tsx
│   │   │   ├── ControlPanel.tsx
│   │   │   ├── AnimationControls.tsx
│   │   │   ├── MetricsDashboard.tsx
│   │   │   ├── AlgorithmComparison.tsx
│   │   │   ├── CacheManager.tsx
│   │   │   ├── SettingsPanel.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   ├── hooks/
│   │   │   ├── useSSEPathfinding.ts
│   │   │   ├── usePlaybackLoop.ts
│   │   │   └── useUserLocation.ts
│   │   ├── stores/
│   │   │   ├── appStore.ts
│   │   │   └── playbackStore.ts
│   │   ├── utils/api.ts
│   │   └── types/index.ts
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/
│   │   │   ├── pathfinding.py
│   │   │   ├── pathfinding_sse.py
│   │   │   ├── cache.py
│   │   │   ├── settings.py
│   │   │   └── metrics.py
│   │   ├── services/pathfinding/
│   │   └── services/graph/
│   ├── tests/
│   └── .env.example
├── docker-compose.yml
├── Dockerfile
└── nginx.conf
```

## Testing & Validation

Backend:

```bash
cd backend
pytest tests -v --cov=app
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

## License

MIT
