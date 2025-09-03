"""
A* algorithm — priority queue with configurable heuristic functions.
"""

import math
import heapq

import networkx as nx

from app.services.pathfinding.base import PathfindingAlgorithm, PathResult


class AStarPathfinder(PathfindingAlgorithm):
    """A* pathfinder with configurable heuristic."""

    HEURISTICS = {"haversine", "manhattan", "euclidean", "zero"}

    def __init__(self, heuristic_type: str = "haversine"):
        super().__init__("astar")
        if heuristic_type not in self.HEURISTICS:
            raise ValueError(
                f"Unknown heuristic: {heuristic_type}. Choose from {self.HEURISTICS}"
            )
        self.heuristic_type = heuristic_type
        self._heuristic_fn = {
            "haversine": self._haversine,
            "manhattan": self._manhattan,
            "euclidean": self._euclidean,
            "zero": self._zero,
        }[heuristic_type]
        self._heuristic_sum = 0.0
        self._actual_cost_sum = 0.0

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great-circle distance in meters."""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _manhattan(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Manhattan distance approximation in meters."""
        lat_diff = abs(lat2 - lat1) * 111_000
        lon_diff = (
            abs(lon2 - lon1) * 111_000 * math.cos(math.radians((lat1 + lat2) / 2))
        )
        return lat_diff + lon_diff

    def _euclidean(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Euclidean distance approximation in meters."""
        lat_diff = (lat2 - lat1) * 111_000
        lon_diff = (lon2 - lon1) * 111_000 * math.cos(math.radians((lat1 + lat2) / 2))
        return math.sqrt(lat_diff**2 + lon_diff**2)

    def _zero(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Zero heuristic — degrades A* to Dijkstra."""
        return 0.0

    def _heuristic(self, graph: nx.DiGraph, node: str, end: str, weight: str) -> float:
        """Compute heuristic value from node to end."""
        node_data = graph.nodes[node]
        end_data = graph.nodes[end]
        h = self._heuristic_fn(
            node_data.get("lat", 0),
            node_data.get("lon", 0),
            end_data.get("lat", 0),
            end_data.get("lon", 0),
        )
        # For time-based weights, convert distance heuristic to time estimate
        if weight == "time":
            # Assume fastest possible speed (motorway) for admissibility
            h = h / 1000 / 130 * 3600  # distance_m -> km -> hours at 130km/h -> seconds
        return h

    async def find_path(
        self,
        graph: nx.DiGraph,
        start: str,
        end: str,
        weight: str = "distance",
        websocket=None,
        config: dict = None,
    ) -> PathResult:
        if start == end:
            self._nodes_explored = 0
            return self._build_result(graph, [start], 0, 0, 0, weight)

        self._begin_tracking()
        self._heuristic_sum = 0.0
        self._actual_cost_sum = 0.0

        # Priority queue: (f_score, counter, node_id)
        counter = 0
        h_start = self._heuristic(graph, start, end, weight)
        pq = [(h_start, counter, start)]
        g_score = {start: 0.0}
        prev = {}
        visited = set()

        while pq:
            f, _, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            current_g = g_score[current]
            await self._stream_visit(
                websocket,
                graph,
                current,
                current_g,
                {"f_score": round(f, 2), "heuristic": self.heuristic_type},
            )

            if current == end:
                path = self._reconstruct_path(prev, start, end)
                time_ms, memory_mb = self._end_tracking()
                effectiveness = (
                    round(self._heuristic_sum / self._actual_cost_sum, 4)
                    if self._actual_cost_sum > 0
                    else 0
                )
                return self._build_result(
                    graph,
                    path,
                    current_g,
                    time_ms,
                    memory_mb,
                    weight,
                    extra={
                        "heuristic_type": self.heuristic_type,
                        "heuristic_effectiveness": effectiveness,
                    },
                )

            for neighbor in graph.successors(current):
                if neighbor in visited:
                    continue
                edge_data = graph[current][neighbor]
                edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                tentative_g = current_g + edge_weight

                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    prev[neighbor] = current
                    h = self._heuristic(graph, neighbor, end, weight)
                    f_score = tentative_g + h
                    counter += 1
                    heapq.heappush(pq, (f_score, counter, neighbor))
                    self._heuristic_sum += h
                    self._actual_cost_sum += edge_weight

            if self._nodes_explored % 50 == 0:
                await self._stream_frontier(websocket, len(pq))

        time_ms, memory_mb = self._end_tracking()
        return self._no_path_result(time_ms, memory_mb)

    def _reconstruct_path(self, prev: dict, start: str, end: str) -> list[str]:
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = prev.get(current)
        path.reverse()
        return path if path and path[0] == start else []
