"""
SSE (Server-Sent Events) endpoint for pathfinding visualization.

Streams the same event types used by the WebSocket API but over HTTP/SSE.
The endpoint accepts query parameters and streams JSON payloads as SSE events
with the format:

    event: {type}\n
data: {json}\n\n
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.core.metrics import metrics
from app.services.pathfinding.engine import run_pathfinding
from app.services.graph.graph_service import graph_service
from app.schemas.pathfinding import AlgorithmType, PathfindingConfig
from app.services.pathfinding.serialization import sanitize_for_json

logger = logging.getLogger("pathfinding.sse")

router = APIRouter()


class QueueSender:
    """A websocket-like adapter that writes messages into an asyncio.Queue.

    This allows existing code that calls `await websocket.send_json(...)` to
    continue working by putting the message dict into the provided queue.
    """

    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self._dropped_events_by_algorithm: dict[str, int] = {}

    async def send_json(self, message: Dict[str, Any]):
        # Drop verbose exploration events if queue is full to avoid memory blow-ups.
        msg_type = message.get("type")
        if self._queue.full() and msg_type in {
            "node_visit",
            "edge_explore",
            "frontier_update",
        }:
            algo = message.get("algorithm")
            if isinstance(algo, str) and algo:
                self._dropped_events_by_algorithm[algo] = (
                    self._dropped_events_by_algorithm.get(algo, 0) + 1
                )
            return

        if msg_type == "complete":
            algo = message.get("algorithm")
            dropped = (
                self._dropped_events_by_algorithm.pop(algo, 0)
                if isinstance(algo, str)
                else 0
            )
            if dropped > 0:
                logger.warning("Dropped %s SSE events for algorithm %s", dropped, algo)
                metrics_payload = message.get("metrics")

                if isinstance(metrics_payload, dict):
                    extra = metrics_payload.get("extra")
                    if not isinstance(extra, dict):
                        extra = {}
                        metrics_payload["extra"] = extra
                    extra["dropped_sse_events"] = dropped

        await self._queue.put(message)


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    return v in {"1", "true", "yes", "on"}


def _build_config_from_query(qs: Dict[str, str]) -> PathfindingConfig:
    # Accept commonly used config query params and coerce types where needed.
    cfg: Dict[str, Any] = {}

    if "astar_heuristic" in qs:
        cfg["astar_heuristic"] = qs["astar_heuristic"]
    if "weight_function" in qs:
        cfg["weight_function"] = qs["weight_function"]
    if "k_paths" in qs:
        try:
            cfg["k_paths"] = int(qs["k_paths"])
        except Exception:
            pass
    if "animation_speed" in qs:
        try:
            cfg["animation_speed"] = float(qs["animation_speed"])
        except Exception:
            pass
    if "show_all_explored" in qs:
        cfg["show_all_explored"] = _parse_bool(qs.get("show_all_explored"))
    if "animation_granularity" in qs:
        cfg["animation_granularity"] = qs["animation_granularity"]
    # Support hybrid weights via hybrid_weights_alpha / hybrid_weights_beta
    alpha = qs.get("hybrid_weights_alpha")
    beta = qs.get("hybrid_weights_beta")
    if alpha is not None or beta is not None:
        hw: Dict[str, Any] = {}
        try:
            if alpha is not None:
                hw["alpha"] = float(alpha)
            if beta is not None:
                hw["beta"] = float(beta)
        except Exception:
            pass
        if hw:
            cfg["hybrid_weights"] = hw

    # Validate via pydantic model (will raise if invalid)
    return PathfindingConfig.model_validate(cfg)


@router.get("/api/pathfinding/stream")
async def pathfinding_sse(
    request: Request,
    start_lat: float = Query(..., alias="start_lat"),
    start_lon: float = Query(..., alias="start_lon"),
    end_lat: float = Query(..., alias="end_lat"),
    end_lon: float = Query(..., alias="end_lon"),
    algorithms: str = Query("astar", alias="algorithms"),
    radius_km: Optional[float] = Query(None, alias="radius_km"),
    request_query: Optional[str] = Query(None),
):
    """Stream pathfinding events as Server-Sent Events (SSE).

    Query parameters:
    - start_lat, start_lon, end_lat, end_lon (required)
    - algorithms: comma-separated algorithm names (default: "astar")
    - optional config params (see `_build_config_from_query` for supported keys)
    """

    # Build algorithm list
    algo_names = [a.strip() for a in algorithms.split(",") if a.strip()]
    algo_types: list[AlgorithmType] = []
    try:
        for name in algo_names:
            algo_types.append(AlgorithmType(name))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid algorithm: {name}")

    # Build config from raw query params
    # FastAPI Request.query_params is a MultiDict; coerce to simple dict of last values
    raw_qs = {k: v for k, v in request.query_params.items()}
    try:
        config = _build_config_from_query(raw_qs)
    except Exception:
        logger.exception("Invalid config from query string")
        raise HTTPException(status_code=400, detail="Invalid configuration parameters")

    queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    sender = QueueSender(queue)

    # Track SSE connection timing
    sse_connect_start = time.perf_counter()
    metrics.increment_sse_active()

    async def sse_generator():
        async def producer():
            """Produce pathfinding events into the queue."""
            try:
                # Send immediate loading event so client knows we're working
                await queue.put(
                    {"type": "loading", "message": "Loading road network..."}
                )
                logger.info(
                    f"SSE: Starting pathfinding from ({start_lat}, {start_lon}) to ({end_lat}, {end_lon})"
                )

                center_lat = (start_lat + end_lat) / 2.0
                center_lon = (start_lon + end_lon) / 2.0

                try:
                    logger.info(
                        f"SSE: Fetching graph for center ({center_lat}, {center_lon}), radius_km={radius_km}"
                    )
                    graph, metadata = await graph_service.get_graph_for_region(
                        center_lat, center_lon, radius_km=radius_km
                    )
                    logger.info(
                        f"SSE: Graph loaded with {metadata.get('node_count', 0)} nodes"
                    )
                except Exception as e:
                    logger.exception("Failed to load graph for region")
                    await queue.put(
                        {"type": "error", "message": f"Failed to load graph: {str(e)}"}
                    )
                    await queue.put({"type": "all_complete"})
                    return

                # Send graph info
                await queue.put({"type": "graph_info", "metadata": metadata})
                if metadata.get("source") == "synthetic":
                    await queue.put(
                        {
                            "type": "warning",
                            "message": "Using synthetic fallback graph (OSM unavailable). Routing may not match real streets.",
                        }
                    )
                try:
                    fallback_pct = float(metadata.get("fallback_speed_pct", 0) or 0)
                except Exception:
                    fallback_pct = 0.0

                try:
                    from app.core.config import settings

                    if metadata.get("source") == "osm" and fallback_pct > getattr(
                        settings, "FALLBACK_SPEED_WARNING_THRESHOLD", 0
                    ):
                        await queue.put(
                            {
                                "type": "warning",
                                "message": (
                                    f"{fallback_pct * 100:.1f}% edges are using fallback speed values; time-based routing may be less accurate."
                                ),
                            }
                        )
                except Exception:
                    pass

                # Find nearest nodes
                start_node = graph_service.find_nearest_node(
                    graph, start_lat, start_lon
                )
                end_node = graph_service.find_nearest_node(graph, end_lat, end_lon)

                if start_node is None or end_node is None:
                    await queue.put(
                        {
                            "type": "error",
                            "message": "Could not find nodes near the specified coordinates",
                        }
                    )
                    await queue.put({"type": "all_complete"})
                    return

                if start_node == end_node:
                    node_data = graph.nodes[start_node]
                    for algo in algo_types:
                        await queue.put(
                            {
                                "type": "complete",
                                "algorithm": algo.value,
                                "requested_algorithm": algo.value,
                                "executed_algorithm": algo.value,
                                "path": [
                                    {
                                        "node_id": start_node,
                                        "lat": node_data.get("lat", start_lat),
                                        "lon": node_data.get("lon", start_lon),
                                    }
                                ],
                                "path_geometry": [],
                                "metrics": {
                                    "nodes_explored": 1,
                                    "path_length_km": 0.0,
                                    "computation_time_ms": 0.0,
                                    "memory_usage_mb": 0.0,
                                    "cost": 0.0,
                                    "path_node_count": 1,
                                    "extra": {
                                        "reason": "start_equals_end",
                                        "requested_algorithm": algo.value,
                                        "executed_algorithm": algo.value,
                                    },
                                },
                                "success": True,
                                "error": None,
                            }
                        )
                    await queue.put(
                        {
                            "type": "warning",
                            "message": "Start and end resolve to same node; returned zero-cost path.",
                        }
                    )
                    await queue.put({"type": "all_complete"})
                    return

                # Run each algorithm sequentially
                for algo_type in algo_types:
                    algo_name = algo_type.value
                    await queue.put({"type": "algorithm_start", "algorithm": algo_name})
                    try:
                        await run_pathfinding(
                            graph,
                            start_node,
                            end_node,
                            algo_type,
                            config,
                            websocket=sender,
                        )
                    except Exception as e:
                        logger.exception(f"Algorithm {algo_name} failed")
                        await queue.put(
                            {
                                "type": "complete",
                                "algorithm": algo_name,
                                "requested_algorithm": algo_name,
                                "executed_algorithm": algo_name,
                                "path": [],
                                "path_geometry": [],
                                "metrics": {
                                    "nodes_explored": 0,
                                    "path_length_km": 0.0,
                                    "computation_time_ms": 0.0,
                                    "memory_usage_mb": 0.0,
                                    "cost": None,
                                    "path_node_count": 0,
                                    "extra": {
                                        "reason": "execution_failed",
                                        "requested_algorithm": algo_name,
                                        "executed_algorithm": algo_name,
                                    },
                                },
                                "success": False,
                                "error": str(e),
                            }
                        )

                await queue.put({"type": "all_complete"})

            except Exception as e:
                logger.exception("Producer failure")
                await queue.put({"type": "error", "message": str(e)})
                await queue.put({"type": "all_complete"})

        # Start producer task
        logger.info("SSE: Starting producer task")
        producer_task = asyncio.create_task(producer())
        first_event_sent = False

        try:
            while True:
                msg = await queue.get()
                ev_type = msg.get("type", "message")
                safe_msg = sanitize_for_json(msg)
                data = json.dumps(safe_msg, default=str, allow_nan=False)
                event_str = f"event: {ev_type}\ndata: {data}\n\n"
                logger.debug(f"SSE: Yielding event {ev_type}")
                yield event_str

                # Record connection time on first event
                if not first_event_sent:
                    connect_time_ms = (time.perf_counter() - sse_connect_start) * 1000
                    metrics.record_sse_connect(connect_time_ms)
                    first_event_sent = True

                if ev_type == "all_complete":
                    logger.info("SSE: All complete, closing stream")
                    metrics.decrement_sse_active()
                    # ensure producer finished
                    try:
                        await producer_task
                    except Exception:
                        pass
                    return
        except asyncio.CancelledError:
            # Client disconnected; cancel producer
            metrics.decrement_sse_active()
            if not producer_task.done():
                producer_task.cancel()
                try:
                    await producer_task
                except Exception:
                    pass
            logger.info("SSE client disconnected")
            return
        except Exception as e:
            logger.exception("Unexpected error in SSE generator")
            metrics.decrement_sse_active()
            if not producer_task.done():
                producer_task.cancel()
            try:
                await queue.put({"type": "error", "message": str(e)})
                await queue.put({"type": "all_complete"})
            except Exception:
                pass
            return

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # Prevent some proxies from buffering SSE
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(
        sse_generator(), media_type="text/event-stream", headers=headers
    )
