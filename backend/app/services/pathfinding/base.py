"""
Abstract base class for all pathfinding algorithms.
Defines the interface for path computation with real-time WebSocket streaming.
"""

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

    def _begin_tracking(self):
        """Start performance tracking."""
        self._nodes_explored = 0
        self._start_time = time.perf_counter()
        tracemalloc.start()
        self._start_memory = tracemalloc.get_traced_memory()[0]

    def _end_tracking(self) -> tuple[float, float]:
        """End performance tracking. Returns (time_ms, memory_mb)."""
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory_mb = (peak - self._start_memory) / (1024 * 1024)
        return round(elapsed_ms, 2), round(max(memory_mb, 0), 4)

    async def _stream_visit(
        self, websocket, graph, node_id: str, cost: float, metadata: dict = None
    ):
        """Stream a node visit event via WebSocket."""
        self._nodes_explored += 1
        if websocket is None:
            return
        node_data = graph.nodes[node_id]
        msg = {
            "type": "node_visit",
            "algorithm": self.name,
            "node_id": node_id,
            "lat": node_data.get("lat", 0),
            "lon": node_data.get("lon", 0),
            "cost": round(cost, 4),
            "nodes_explored": self._nodes_explored,
            "metadata": metadata or {},
        }
        try:
            await websocket.send_json(msg)
        except Exception:
            pass  # WebSocket may be closed

    async def _stream_frontier(self, websocket, frontier_size: int):
        """Stream a frontier update."""
        if websocket is None:
            return
        msg = {
            "type": "frontier_update",
            "algorithm": self.name,
            "frontier_size": frontier_size,
            "nodes_explored": self._nodes_explored,
        }
        try:
            await websocket.send_json(msg)
        except Exception:
            pass

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
                prev = graph.nodes[path[i - 1]]
                curr = node_data
                path_length_km += (
                    haversine_distance(
                        prev.get("lat", 0),
                        prev.get("lon", 0),
                        curr.get("lat", 0),
                        curr.get("lon", 0),
                    )
                    / 1000
                )

        return PathResult(
            algorithm=self.name,
            path=path,
            path_coords=path_coords,
            cost=round(cost, 4),
            nodes_explored=self._nodes_explored,
            computation_time_ms=time_ms,
            memory_usage_mb=memory_mb,
            path_length_km=round(path_length_km, 4),
            extra=extra or {},
        )

    def _no_path_result(self, time_ms: float, memory_mb: float) -> PathResult:
        """Return a result indicating no path was found."""
        return PathResult(
            algorithm=self.name,
            path=[],
            path_coords=[],
            cost=float("inf"),
            nodes_explored=self._nodes_explored,
            computation_time_ms=time_ms,
            memory_usage_mb=memory_mb,
            path_length_km=0,
            success=False,
            error="No path found between start and end nodes.",
        )
