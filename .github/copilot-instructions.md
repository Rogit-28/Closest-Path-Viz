# Copilot instructions for Closest-Path-Viz

## Build, test, and lint commands

### Frontend (`frontend`)
- Install: `npm install`
- Dev server: `npm run dev`
- Build: `npm run build`
- Lint: `npm run lint`
- Lint one file: `npm run lint -- src/components/MapView.tsx`

### Backend (`backend`)
- Install dependencies: `pip install -r requirements.txt`
- Run API locally: `uvicorn app.main:app --reload --port 8000`
- Run all tests: `pytest tests -v --cov=app`
- Run a single test function: `pytest tests/unit/test_algorithms.py::test_dijkstra_simple_path -v`
- Run one test class/test by filter: `pytest tests/integration/test_api.py -k algorithms_list -v`
- Lint/type tools available via `requirements.txt`: `ruff check app tests`, `black --check app tests`, `mypy app`

### Full stack
- `docker-compose up --build`

## High-level architecture

- The frontend is a React + Vite + TypeScript app with Zustand global state (`frontend/src/stores/appStore.ts`) and MapLibre rendering (`MapView.tsx`).
- UI flow is map-driven: left-click sets `startPoint`, right-click (`contextmenu`) sets `endPoint`; `ControlPanel` triggers pathfinding.
- Real-time execution uses WebSocket (`/ws/pathfinding`): frontend `useWebSocket` sends request payload; backend `app/websockets.py` streams `graph_info`, `algorithm_start`, `node_visit`, `frontier_update`, `complete`, `all_complete`, and `error`.
- REST endpoints in `backend/app/api/routes/pathfinding.py` provide non-streaming runs (`/find-path`), algorithm metadata, benchmark, and compare APIs.
- Pathfinding orchestration is in `backend/app/services/pathfinding/engine.py`; concrete algorithms implement the shared async interface in `base.py`.
- Graph loading/caching is in `backend/app/services/graph/graph_service.py`: in-memory cache + JSON file cache (`GRAPH_CACHE_DIR`) + OSM fetch; if OSM/osmnx fails, it falls back to a synthetic grid graph.
- DB/Redis are optional at startup (`app/main.py` lifespan). App logs warnings and continues when unavailable.
- Cache and user settings routes currently use in-memory stores (`cache_service.py`, `routes/settings.py`), not persisted database-backed state.

## Key conventions for this repository

- Keep algorithm identifiers synchronized across:
  - backend enums (`AlgorithmType` in `backend/app/schemas/pathfinding.py`)
  - frontend unions/constants (`frontend/src/types/index.ts`)
  - UI labels/colors (`ALGORITHM_NAMES`, `ALGORITHM_COLORS`)
  - map layer IDs (`path-${algorithm}` in `MapView.tsx`)
- Graph nodes must have `lat`/`lon`, and edges must carry `distance` and `time` for weight switching to work.
- `weight_function=hybrid` depends on precomputed `edge["hybrid"]` in the engine.
- `k_paths > 1` in config routes execution through Yen’s K-shortest implementation regardless of selected base algorithm.
- Floyd-Warshall is guarded by `FLOYD_WARSHALL_NODE_LIMIT`; WebSocket runs it on a truncated subgraph when needed.
- Frontend API calls assume Vite proxy (`/api` and `/ws`) in `vite.config.ts`; do not hardcode backend host in components/hooks.
- The active runtime hook is `useWebSocket`; `usePathfinding.ts` is not wired into `App.tsx`.
- Backend tests are the primary automated tests in-repo (`backend/tests/unit`, `backend/tests/integration`); no frontend test runner is currently configured.
