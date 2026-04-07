# Pathfinding Visualization Platform

Real-time pathfinding algorithm visualization on OpenStreetMap road networks. Compare Dijkstra, A\*, Bidirectional Search, Bellman-Ford, and Floyd-Warshall side-by-side with animated node exploration, interactive maps, and performance metrics.

![Tech Stack](https://img.shields.io/badge/React_18-TypeScript-blue) ![Backend](https://img.shields.io/badge/FastAPI-Python-green) ![Map](https://img.shields.io/badge/MapLibre_GL_JS-purple)

## Features

- **5 Pathfinding Algorithms** — Dijkstra, A\*, Bidirectional Dijkstra, Bellman-Ford, Floyd-Warshall
- **Real-time Visualization** — WebSocket-streamed junction + street exploration (node visits + outgoing edge candidates) with animated rendering
- **Algorithm Comparison** — Run multiple algorithms simultaneously with radar charts and metrics tables
- **Interactive Map** — Click to set start/end points on a MapLibre dark-theme map (OpenStreetMap + CARTO tiles)
- **Configurable Parameters** — Heuristic functions (Haversine, Manhattan, Euclidean), weight functions (distance, time, hybrid), K-shortest paths
- **Metrics Dashboard** — Computation time, nodes explored, path length, memory usage with Recharts bar charts
- **Settings Panel** — Full user preferences for pathfinding defaults, visualization speed, and cache management
- **Cache Management** — Pre-cached city graphs with configurable refresh schedules
- **Synthetic Fallback** — Demo mode generates a grid graph when OSM data is unavailable

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Frontend (React 18 + TypeScript + Vite)                   │
│  ├── MapLibre GL JS — map rendering + GeoJSON layers       │
│  ├── Zustand — global state management                     │
│  ├── Recharts — metrics bar charts + radar comparison      │
│  ├── Tailwind CSS — dark theme UI                          │
│  └── WebSocket client — real-time algorithm streaming      │
├────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python)                                │
│  ├── Pathfinding Engine — 5 algorithm implementations      │
│  │   ├── dijkstra.py — standard priority queue             │
│  │   ├── astar.py — 4 configurable heuristics              │
│  │   ├── bidirectional.py — forward/backward search        │
│  │   ├── bellman_ford.py — negative cycle detection         │
│  │   ├── floyd_warshall.py — numpy matrix all-pairs        │
│  │   └── yen_k_shortest.py — K-shortest paths              │
│  ├── Graph Service — OSM via osmnx + synthetic fallback    │
│  ├── WebSocket handler — node visit streaming              │
│  ├── Cache Service — 50 top cities, schedule CRUD          │
│  └── Benchmarking — performance comparison suite           │
├────────────────────────────────────────────────────────────┤
│  Infrastructure                                            │
│  ├── PostgreSQL + PostGIS — spatial data storage            │
│  ├── Redis — graph caching layer                           │
│  ├── Celery — async cache refresh tasks                    │
│  ├── Docker Compose — full orchestration                   │
│  └── Nginx — reverse proxy                                 │
└────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11 (recommended)
- **Docker & Docker Compose** (optional, for full stack)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.
Map rendering is tokenless by default via MapLibre + OpenStreetMap/CARTO raster tiles.
Without the backend, the map still renders but pathfinding requests will show connection/errors.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.
For real-road routing fidelity (not synthetic fallback), ensure `osmnx` installs successfully in the backend environment.

### Docker (Full Stack)

```bash
docker compose up --build
```

This starts PostgreSQL+PostGIS, Redis, the FastAPI backend, and Nginx.
The Postgres service is internal to the Compose network (no host DB port binding by default).

## Configuration

Copy `backend/.env.example` to `backend/.env` and configure:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pathfinding
REDIS_URL=redis://localhost:6379/0
```

The backend gracefully degrades — it starts without PostgreSQL or Redis, falling back to in-memory storage.
When OSM fetch fails or `osmnx` is missing, the app falls back to a synthetic graph and now surfaces an in-app warning. In that mode, routes may not follow real streets.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pathfinding/find-path` | Run pathfinding with selected algorithms |
| `GET` | `/api/pathfinding/algorithms` | List available algorithms |
| `POST` | `/api/pathfinding/benchmark` | Benchmark algorithms with N iterations |
| `GET` | `/api/pathfinding/compare` | Compare algorithm performance |
| `WS` | `/ws/pathfinding` | WebSocket for real-time node + edge exploration streaming + geometry-aware final paths |
| `GET` | `/api/cache/cities` | List cached cities |
| `POST` | `/api/cache/refresh` | Refresh/defer a city cache by id |
| `POST` | `/api/cache/schedule` | Set a city's cache schedule |
| `GET` | `/api/user/settings` | Get user settings |
| `PUT` | `/api/user/settings` | Update user settings |
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Frontend configuration |

## Algorithms

| Algorithm | Time Complexity | Space | Best For |
|-----------|----------------|-------|----------|
| **Dijkstra** | O((V+E) log V) | O(V) | Guaranteed shortest path |
| **A\*** | O((V+E) log V) | O(V) | Faster with good heuristic |
| **Bidirectional** | O((V+E) log V) | O(V) | Reduces search space ~50% |
| **Bellman-Ford** | O(V·E) | O(V) | Handles negative weights |
| **Floyd-Warshall** | O(V³) | O(V²) | All-pairs shortest paths |
| **Yen's K-Shortest** | O(KV(V+E) log V) | O(KV) | Alternative route options |

## Project Structure

```
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── MapView.tsx          # MapLibre GL map with GeoJSON layers
│   │   │   ├── ControlPanel.tsx     # Algorithm selection + config sidebar
│   │   │   ├── AnimationControls.tsx # Play/pause/speed floating bar
│   │   │   ├── MetricsDashboard.tsx  # Results + Recharts bar charts
│   │   │   ├── AlgorithmComparison.tsx # Radar chart + comparison table
│   │   │   ├── SettingsPanel.tsx     # Full settings modal
│   │   │   └── CacheManager.tsx      # City cache management
│   │   ├── stores/appStore.ts   # Zustand global state
│   │   ├── hooks/               # useWebSocket, usePathfinding
│   │   ├── types/index.ts       # Shared TypeScript types
│   │   ├── utils/api.ts         # REST API client
│   │   └── styles/              # Tailwind + visualization CSS
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory + WebSocket route
│   │   ├── websockets.py        # WebSocket handler + ConnectionManager
│   │   ├── core/                # Config, database, Redis, Celery
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── api/routes/          # REST endpoints
│   │   └── services/
│   │       ├── graph/           # OSM graph loading + synthetic fallback
│   │       ├── pathfinding/     # Algorithm implementations
│   │       ├── cache/           # City cache management
│   │       └── benchmarking.py  # Performance testing
│   ├── tests/                   # Unit + integration tests
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml
├── Dockerfile
└── .gitignore
```

## Testing

```bash
cd backend
pytest tests/ -v --cov=app
```

Run a single test:

```bash
cd backend
pytest tests/unit/test_algorithms.py::test_dijkstra_simple_path -v
```

## License

MIT
