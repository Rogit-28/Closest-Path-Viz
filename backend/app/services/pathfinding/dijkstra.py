"""
Dijkstra's algorithm — standard priority queue implementation.
"""

import heapq
from typing import Optional

import networkx as nx

from app.services.pathfinding.base import PathfindingAlgorithm, PathResult


class DijkstraPathfinder(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("dijkstra")

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

        # Priority queue: (cost, node_id)
        pq = [(0.0, start)]
        dist = {start: 0.0}
        prev = {}
        visited = set()

        while pq:
            current_cost, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            await self._stream_visit(websocket, graph, current, current_cost)

            if current == end:
                # Reconstruct path
                path = self._reconstruct_path(prev, start, end)
                time_ms, memory_mb = self._end_tracking()
                return self._build_result(
                    graph, path, current_cost, time_ms, memory_mb, weight
                )

            for neighbor in graph.successors(current):
                if neighbor in visited:
                    continue
                edge_data = graph[current][neighbor]
                edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                new_cost = current_cost + edge_weight

                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    prev[neighbor] = current
                    heapq.heappush(pq, (new_cost, neighbor))

            # Stream frontier update every 50 nodes
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
        return path if path[0] == start else []
