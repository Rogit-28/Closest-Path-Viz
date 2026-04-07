"""
Yen's algorithm for finding K-shortest paths.
"""

import heapq
from typing import Optional, List

import networkx as nx

from app.services.pathfinding.base import PathfindingAlgorithm, PathResult


class YensKShortestPathfinder(PathfindingAlgorithm):
    """Yen's K-shortest paths algorithm."""

    def __init__(self, k: int = 5):
        super().__init__("yens_k_shortest")
        self.k = min(k, 10)  # Limit to 10 to prevent memory issues

    async def find_path(
        self,
        graph: nx.DiGraph,
        start: str,
        end: str,
        weight: str = "distance",
        websocket=None,
        config: dict = None,
    ) -> PathResult:
        """
        Find K-shortest paths using Yen's algorithm.

        Returns the shortest path as primary result, with K paths in extra.
        Time complexity: O(K * V * (E + V*log(V)))
        """
        if start == end:
            self._nodes_explored = 0
            return self._build_result(graph, [start], 0, 0, 0, weight)

        self._begin_tracking(config)

        # Get k shortest paths
        k_paths = await self._find_k_shortest_paths(
            graph, start, end, weight, websocket, config
        )

        time_ms, memory_mb = self._end_tracking()

        if not k_paths:
            return self._no_path_result(time_ms, memory_mb)

        # Primary result is shortest path
        best_path, best_cost = k_paths[0]

        # Format other paths for extra
        other_paths = [
            {"path": path, "cost": cost, "length": len(path)}
            for path, cost in k_paths[1:]
        ]

        return self._build_result(
            graph,
            best_path,
            best_cost,
            time_ms,
            memory_mb,
            weight,
            extra={
                "k": self.k,
                "k_paths": k_paths,
                "num_found": len(k_paths),
                "other_paths": other_paths,
            },
        )

    async def _find_k_shortest_paths(
        self,
        graph: nx.DiGraph,
        start: str,
        end: str,
        weight: str,
        websocket,
        config: dict | None = None,
    ) -> List[tuple]:
        """Find K shortest paths using Yen's algorithm."""
        # Get shortest path first (using Dijkstra with streaming)
        hybrid_resolver = (config or {}).get("hybrid_resolver") if config else None
        shortest = await self._dijkstra_with_streaming(
            graph, start, end, weight, hybrid_resolver, websocket
        )

        if shortest is None:
            return []

        k_shortest = [shortest]
        candidate_paths = []

        # Generate K-1 more paths
        for k_iter in range(1, self.k):
            # For each node in the shortest path (except last)
            for i in range(len(k_shortest[-1][0]) - 1):
                spur_node = k_shortest[-1][0][i]
                root_path = k_shortest[-1][0][: i + 1]

                # Remove edges from spur node used in shorter paths
                removed_edges = set()
                for path, _ in k_shortest:
                    if len(path) > i + 1 and path[: i + 1] == root_path:
                        removed_edges.add((path[i], path[i + 1]))

                # Find spur path with constraints
                spur_path = await self._dijkstra_with_excluded_edges(
                    graph, spur_node, end, weight, removed_edges, hybrid_resolver
                )

                if spur_path is not None:
                    full_path = root_path[:-1] + spur_path[0]
                    full_cost = self._calculate_path_cost(
                        graph, full_path, weight, hybrid_resolver
                    )
                    candidate = (full_path, full_cost)

                    # Avoid duplicates - convert paths to tuples for comparison
                    existing_paths = {tuple(path) for path, _ in k_shortest}
                    candidate_path_tuples = {
                        tuple(cand[0]) for _, _, cand in candidate_paths
                    }

                    if (
                        tuple(full_path) not in existing_paths
                        and tuple(full_path) not in candidate_path_tuples
                    ):
                        heapq.heappush(
                            candidate_paths, (full_cost, id(candidate), candidate)
                        )

            if not candidate_paths:
                break

            # Get next best candidate path
            _, _, next_path = heapq.heappop(candidate_paths)
            k_shortest.append(next_path)

            # Stream progress
            await self._stream_visit(
                websocket,
                graph,
                next_path[0][-1],
                next_path[1],
                {"k_iteration": k_iter, "path_length": len(next_path[0])},
            )
        return k_shortest

    async def _dijkstra_with_streaming(
        self,
        graph: nx.DiGraph,
        start: str,
        end: str,
        weight: str,
        hybrid_resolver=None,
        websocket=None,
    ) -> Optional[tuple]:
        """Dijkstra with visual event streaming for first K-path."""
        dist = {node: float("inf") for node in graph.nodes()}
        dist[start] = 0.0
        prev = {}
        visited = set()
        pq = [(0.0, start)]

        while pq:
            current_cost, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            # Stream node visit
            self._nodes_explored += 1
            await self._stream_visit(websocket, graph, current, current_cost)

            if current == end:
                path = self._reconstruct_path(prev, start, end)
                return (path, current_cost)

            for neighbor in graph.successors(current):
                if neighbor in visited:
                    continue
                edge_data = graph[current][neighbor]
                if weight == "hybrid" and hybrid_resolver is not None:
                    edge_weight = hybrid_resolver(edge_data)
                else:
                    edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                new_cost = current_cost + edge_weight

                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    prev[neighbor] = current
                    heapq.heappush(pq, (new_cost, neighbor))

                    # Stream edge exploration
                    await self._stream_edge(
                        websocket,
                        graph,
                        current,
                        neighbor,
                        new_cost,
                        {"improved": True},
                    )

        return None

    async def _dijkstra(
        self,
        graph: nx.DiGraph,
        start: str,
        end: str,
        weight: str,
        hybrid_resolver=None,
    ) -> Optional[tuple]:
        """Standard Dijkstra with path cost returned."""
        dist = {node: float("inf") for node in graph.nodes()}
        dist[start] = 0.0
        prev = {}
        visited = set()
        pq = [(0.0, start)]

        while pq:
            current_cost, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == end:
                path = self._reconstruct_path(prev, start, end)
                return (path, current_cost)

            for neighbor in graph.successors(current):
                if neighbor in visited:
                    continue
                edge_data = graph[current][neighbor]
                if weight == "hybrid" and hybrid_resolver is not None:
                    edge_weight = hybrid_resolver(edge_data)
                else:
                    edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                new_cost = current_cost + edge_weight

                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    prev[neighbor] = current
                    heapq.heappush(pq, (new_cost, neighbor))

        return None

    async def _dijkstra_with_excluded_edges(
        self,
        graph: nx.DiGraph,
        start: str,
        end: str,
        weight: str,
        excluded: set,
        hybrid_resolver=None,
    ) -> Optional[tuple]:
        """Dijkstra with excluded edges."""
        dist = {node: float("inf") for node in graph.nodes()}
        dist[start] = 0.0
        prev = {}
        visited = set()
        pq = [(0.0, start)]

        while pq:
            current_cost, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == end:
                path = self._reconstruct_path(prev, start, end)
                return (path, current_cost)

            for neighbor in graph.successors(current):
                # Skip excluded edges
                if (current, neighbor) in excluded:
                    continue
                if neighbor in visited:
                    continue

                edge_data = graph[current][neighbor]
                if weight == "hybrid" and hybrid_resolver is not None:
                    edge_weight = hybrid_resolver(edge_data)
                else:
                    edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                new_cost = current_cost + edge_weight

                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    prev[neighbor] = current
                    heapq.heappush(pq, (new_cost, neighbor))

        return None

    def _reconstruct_path(self, prev: dict, start: str, end: str) -> list[str]:
        """Reconstruct path from predecessors."""
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = prev.get(current)
        path.reverse()
        return path if path and path[0] == start else []

    def _calculate_path_cost(
        self, graph: nx.DiGraph, path: list[str], weight: str, hybrid_resolver=None
    ) -> float:
        """Calculate total cost of a path."""
        cost = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if graph.has_edge(u, v):
                edge_data = graph[u][v]
                if weight == "hybrid" and hybrid_resolver is not None:
                    edge_weight = hybrid_resolver(edge_data)
                else:
                    edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                cost += edge_weight
            else:
                return float("inf")
        return cost
