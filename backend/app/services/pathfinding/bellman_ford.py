"""
Bellman-Ford algorithm — shortest path with negative edge support and cycle detection.
"""

import networkx as nx

from app.services.pathfinding.base import PathfindingAlgorithm, PathResult


class BellmanFordPathfinder(PathfindingAlgorithm):
    """Bellman-Ford pathfinder with negative cycle detection."""

    def __init__(self):
        super().__init__("bellman_ford")

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
        Find shortest path using Bellman-Ford algorithm.
        
        Handles negative weights and detects negative cycles.
        Time complexity: O(V * E)
        """
        if start == end:
            self._nodes_explored = 0
            return self._build_result(graph, [start], 0, 0, 0, weight)

        self._begin_tracking()

        # Initialize distances and predecessors
        dist = {node: float("inf") for node in graph.nodes()}
        dist[start] = 0.0
        prev = {}

        # Relax edges up to V-1 times
        num_nodes = len(graph.nodes())
        for iteration in range(num_nodes - 1):
            edges_relaxed = 0
            
            for u in graph.nodes():
                if dist[u] == float("inf"):
                    continue
                
                for v in graph.successors(u):
                    edge_data = graph[u][v]
                    edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                    
                    if dist[u] + edge_weight < dist[v]:
                        dist[v] = dist[u] + edge_weight
                        prev[v] = u
                        edges_relaxed += 1
                        
                        # Stream node visit
                        await self._stream_visit(
                            websocket,
                            graph,
                            v,
                            dist[v],
                            {"iteration": iteration, "edges_relaxed": edges_relaxed},
                        )
                        self._nodes_explored += 1
            
            # Stream frontier update
            if self._nodes_explored % 100 == 0:
                await self._stream_frontier(websocket, len(graph.nodes()))
            
            # Early termination if no edges were relaxed
            if edges_relaxed == 0:
                break

        # Check for negative cycles
        negative_cycle_detected = False
        negative_cycle_nodes = set()
        
        for u in graph.nodes():
            if dist[u] == float("inf"):
                continue
            
            for v in graph.successors(u):
                edge_data = graph[u][v]
                edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                
                if dist[u] + edge_weight < dist[v]:
                    negative_cycle_detected = True
                    negative_cycle_nodes.add(v)

        time_ms, memory_mb = self._end_tracking()

        # If negative cycle found, report error
        if negative_cycle_detected:
            result = self._no_path_result(time_ms, memory_mb)
            result.error = f"Negative cycle detected involving nodes: {negative_cycle_nodes}"
            result.success = False
            result.extra = {"negative_cycle_nodes": list(negative_cycle_nodes)}
            return result

        # If end is unreachable
        if dist[end] == float("inf"):
            return self._no_path_result(time_ms, memory_mb)

        # Reconstruct path
        path = self._reconstruct_path(prev, start, end)

        return self._build_result(
            graph,
            path,
            dist[end],
            time_ms,
            memory_mb,
            weight,
            extra={"iterations": num_nodes - 1},
        )

    def _reconstruct_path(self, prev: dict, start: str, end: str) -> list[str]:
        """Reconstruct path from predecessors."""
        path = []
        current = end
        while current is not None:
            path.append(current)
            current = prev.get(current)
        path.reverse()
        return path if path and path[0] == start else []
