"""
Abstract base class for all pathfinding algorithms.
Defines the interface for path computation with real-time WebSocket streaming.

IMPORTANT: Algorithm computation runs at FULL SPEED with no delays.
Animation delays are applied ONLY when streaming events to the client AFTER
the algorithm completes. This ensures accurate computation time measurements.
"""

import asyncio
import time
import tracemalloc
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field

import networkx as nx


@dataclass
class PathResult:
    """Result of a pathfinding computation."""

    algorithm: str
    path: list[str]  # list of node IDs
    path_coords: list[dict]  # [{lat, lon}, ...]
    path_geometry: list[list[float]]  # [[lon, lat], ...]
    cost: float
    nodes_explored: int
    computation_time_ms: float
    memory_usage_mb: float
    path_length_km: float
    extra: dict = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class PathfindingAlgorithm(ABC):
    """Abstract base class for pathfinding algorithms."""

    def __init__(self, name: str):
        self.name = name
        self._nodes_explored = 0
        self._start_time = 0.0
        self._start_memory = 0
        self._stream_config: dict = {}
        # Event buffer for post-algorithm streaming
        self._event_buffer: list[dict] = []
        self._websocket = None
        self._max_event_buffer = 20000
        self._dropped_event_count = 0

    @abstractmethod
    async def find_path(
        self,
        graph: nx.DiGraph,
        start: str,
        end: str,
        weight: str,
        websocket=None,
        config: dict = None,
    ) -> PathResult:
        """
        Find the shortest path between start and end nodes.

        Args:
            graph: NetworkX directed graph
            start: Start node ID
            end: End node ID
            weight: Edge weight attribute name ('distance', 'time', or computed)
            websocket: Optional WebSocket for streaming node visits
            config: Optional algorithm-specific configuration
        """
        pass

    def _begin_tracking(self, config: Optional[dict] = None):
        """Start performance tracking."""
        self._nodes_explored = 0
        self._start_time = time.perf_counter()
        tracemalloc.start()
        self._start_memory = tracemalloc.get_traced_memory()[0]
        self._stream_config = config or {}
        # Clear event buffer for this run
        self._event_buffer = []
        self._dropped_event_count = 0

    def _end_tracking(self) -> tuple[float, float]:
        """End performance tracking. Returns (time_ms, memory_mb)."""
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory_mb = (peak - self._start_memory) / (1024 * 1024)
        return round(elapsed_ms, 2), round(max(memory_mb, 0), 4)

    def _animation_granularity(self) -> str:
        granularity = str(
            self._stream_config.get("animation_granularity", "every_node")
        )
        return (
            granularity
            if granularity in {"every_node", "every_n", "frontier_only"}
            else "every_node"
        )

    def _animation_every_n(self) -> int:
        raw = self._stream_config.get("animation_every_n", 10)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 10
        return max(value, 1)

    def _show_all_explored(self) -> bool:
        return bool(self._stream_config.get("show_all_explored", True))

    def _event_algorithm(self) -> str:
        val = self._stream_config.get("event_algorithm")
        if isinstance(val, str) and val:
            return val
        return self.name

    async def _flush_events(self, websocket):
        """Stream all buffered events to the client as fast as possible.

        Animation timing is now controlled client-side for real-time speed control.
        Events are sent rapidly with minimal delay to prevent network flooding.
        """
        if websocket is None or not self._event_buffer:
            return

        # Send events in batches to prevent overwhelming the network
        # Small delay every N events to allow network buffers to flush
        batch_size = 100
        batch_delay = 0.001  # 1ms pause every 100 events

        for i, event in enumerate(self._event_buffer):
            try:
                await websocket.send_json(event)
                # Small pause every batch_size events to prevent flooding
                if (i + 1) % batch_size == 0:
                    await asyncio.sleep(batch_delay)
            except Exception:
                break  # WebSocket closed, stop sending

        # Clear buffer after flushing
        self._event_buffer = []

    def _append_event(self, event: dict):
        """Append event with bounded buffer growth."""
        if len(self._event_buffer) < self._max_event_buffer:
            self._event_buffer.append(event)
            return
        self._dropped_event_count += 1

    def _should_emit_node_visit(self) -> bool:
        if not self._show_all_explored():
            return False
        granularity = self._animation_granularity()
        if granularity == "frontier_only":
            return False
        if granularity == "every_n":
            n = self._animation_every_n()
            return self._nodes_explored == 1 or self._nodes_explored % n == 0
        return True

    def _should_emit_edge(self) -> bool:
        if not self._show_all_explored():
            return False
        granularity = self._animation_granularity()
        if granularity == "frontier_only":
            return False
        if granularity == "every_n":
            n = self._animation_every_n()
            return self._nodes_explored == 1 or self._nodes_explored % n == 0
        return True

    async def _stream_visit(
        self, websocket, graph, node_id: str, cost: float, metadata: dict = None
    ):
        """Buffer a node visit event for later streaming.

        NOTE: This does NOT send immediately - events are buffered and
        sent after algorithm completes via _flush_events().
        """
        self._nodes_explored += 1
        if websocket is None or not self._should_emit_node_visit():
            return
        node_data = graph.nodes[node_id]
        msg = {
            "type": "node_visit",
            "algorithm": self._event_algorithm(),
            "node_id": node_id,
            "lat": node_data.get("lat", 0),
            "lon": node_data.get("lon", 0),
            "cost": round(cost, 4),
            "nodes_explored": self._nodes_explored,
            "metadata": metadata or {},
        }
        # Buffer the event instead of sending immediately
        self._append_event(msg)

    async def _stream_frontier(self, websocket, frontier_size: int):
        """Buffer a frontier update for later streaming."""
        if websocket is None:
            return
        msg = {
            "type": "frontier_update",
            "algorithm": self._event_algorithm(),
            "frontier_size": frontier_size,
            "nodes_explored": self._nodes_explored,
        }
        self._append_event(msg)

    async def _stream_edge(
        self,
        websocket,
        graph,
        from_node_id: str,
        to_node_id: str,
        cost: float,
        metadata: dict = None,
    ):
        """Buffer an explored edge event for later streaming."""
        if websocket is None or not self._should_emit_edge():
            return
        from_node = graph.nodes[from_node_id]
        to_node = graph.nodes[to_node_id]
        edge_geometry = None
        if graph.has_edge(from_node_id, to_node_id):
            edge_geometry = graph[from_node_id][to_node_id].get("geometry")
        msg = {
            "type": "edge_explore",
            "algorithm": self._event_algorithm(),
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "from_lat": from_node.get("lat", 0),
            "from_lon": from_node.get("lon", 0),
            "to_lat": to_node.get("lat", 0),
            "to_lon": to_node.get("lon", 0),
            "cost": round(cost, 4),
            "nodes_explored": self._nodes_explored,
            "geometry": edge_geometry,
            "metadata": metadata or {},
        }
        self._append_event(msg)

    def _build_result(
        self,
        graph: nx.DiGraph,
        path: list[str],
        cost: float,
        time_ms: float,
        memory_mb: float,
        weight: str,
        extra: dict = None,
    ) -> PathResult:
        """Build a PathResult from computed path."""
        from app.services.graph.graph_service import haversine_distance

        path_coords = []
        path_length_km = 0.0
        path_geometry = self._build_path_geometry(graph, path)

        for i, nid in enumerate(path):
            node_data = graph.nodes[nid]
            path_coords.append(
                {
                    "node_id": nid,
                    "lat": node_data.get("lat", 0),
                    "lon": node_data.get("lon", 0),
                }
            )
            if i > 0:
                prev_id = path[i - 1]
                prev = graph.nodes[prev_id]
                curr = node_data
                edge_distance_m = None
                if graph.has_edge(prev_id, nid):
                    raw_distance = graph[prev_id][nid].get("distance")
                    if isinstance(raw_distance, (int, float)):
                        edge_distance_m = float(raw_distance)

                if edge_distance_m is not None:
                    path_length_km += edge_distance_m / 1000
                else:
                    path_length_km += (
                        haversine_distance(
                            prev.get("lat", 0),
                            prev.get("lon", 0),
                            curr.get("lat", 0),
                            curr.get("lon", 0),
                        )
                        / 1000
                    )

        result_extra = dict(extra or {})
        if self._dropped_event_count > 0:
            result_extra.setdefault("dropped_events", self._dropped_event_count)

        return PathResult(
            algorithm=self.name,
            path=path,
            path_coords=path_coords,
            path_geometry=path_geometry,
            cost=round(cost, 4),
            nodes_explored=self._nodes_explored,
            computation_time_ms=time_ms,
            memory_usage_mb=memory_mb,
            path_length_km=round(path_length_km, 4),
            extra=result_extra,
        )

    def _no_path_result(self, time_ms: float, memory_mb: float) -> PathResult:
        """Return a result indicating no path was found."""
        result_extra = {}
        if self._dropped_event_count > 0:
            result_extra["dropped_events"] = self._dropped_event_count
        return PathResult(
            algorithm=self.name,
            path=[],
            path_coords=[],
            path_geometry=[],
            cost=float("nan"),
            nodes_explored=self._nodes_explored,
            computation_time_ms=time_ms,
            memory_usage_mb=memory_mb,
            path_length_km=0,
            extra=result_extra,
            success=False,
            error="No path found between start and end nodes.",
        )

    @staticmethod
    def _coord_distance_sq(
        lon_a: float, lat_a: float, lon_b: float, lat_b: float
    ) -> float:
        dx = lon_a - lon_b
        dy = lat_a - lat_b
        return dx * dx + dy * dy

    def _build_path_geometry(
        self, graph: nx.DiGraph, path: list[str]
    ) -> list[list[float]]:
        """Build a continuous geometry polyline that follows real edge geometries."""
        if len(path) < 2:
            return []

        geometry: list[list[float]] = []

        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]
            from_node = graph.nodes[from_id]
            to_node = graph.nodes[to_id]

            segment: list[list[float]] | None = None
            if graph.has_edge(from_id, to_id):
                raw_geometry = graph[from_id][to_id].get("geometry")
                if isinstance(raw_geometry, list) and len(raw_geometry) >= 2:
                    try:
                        segment = [
                            [float(coord[0]), float(coord[1])]
                            for coord in raw_geometry
                            if isinstance(coord, (list, tuple)) and len(coord) >= 2
                        ]
                    except (TypeError, ValueError):
                        segment = None

            if segment is None or len(segment) < 2:
                segment = [
                    [float(from_node.get("lon", 0)), float(from_node.get("lat", 0))],
                    [float(to_node.get("lon", 0)), float(to_node.get("lat", 0))],
                ]
            else:
                from_lon = float(from_node.get("lon", 0))
                from_lat = float(from_node.get("lat", 0))
                to_lon = float(to_node.get("lon", 0))
                to_lat = float(to_node.get("lat", 0))
                as_is_score = self._coord_distance_sq(
                    segment[0][0], segment[0][1], from_lon, from_lat
                ) + self._coord_distance_sq(
                    segment[-1][0], segment[-1][1], to_lon, to_lat
                )
                reversed_score = self._coord_distance_sq(
                    segment[-1][0], segment[-1][1], from_lon, from_lat
                ) + self._coord_distance_sq(
                    segment[0][0], segment[0][1], to_lon, to_lat
                )
                if reversed_score < as_is_score:
                    segment.reverse()

            if not geometry:
                geometry.extend(segment)
                continue

            if geometry[-1][0] == segment[0][0] and geometry[-1][1] == segment[0][1]:
                geometry.extend(segment[1:])
            else:
                geometry.extend(segment)

        return geometry
