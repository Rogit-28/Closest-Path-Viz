"""
Floyd-Warshall algorithm — all-pairs shortest paths with dynamic programming.
"""

import networkx as nx

from app.services.pathfinding.base import PathfindingAlgorithm, PathResult


class FloydWarshallPathfinder(PathfindingAlgorithm):
    """Floyd-Warshall pathfinder for all-pairs shortest paths."""

    def __init__(self):
        super().__init__("floyd_warshall")

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
        Find shortest path using Floyd-Warshall algorithm.
        
        Computes all-pairs shortest paths via dynamic programming.
        Time complexity: O(V^3)
        Space complexity: O(V^2)
        """
        if start == end:
            self._nodes_explored = 0
            return self._build_result(graph, [start], 0, 0, 0, weight)

        self._begin_tracking()

        nodes = list(graph.nodes())
        n = len(nodes)
        node_idx = {node: i for i, node in enumerate(nodes)}
        
        # Initialize distance matrix
        dist = [[float("inf")] * n for _ in range(n)]
        next_node = [[None] * n for _ in range(n)]
        
        # Base case: self-loops are 0
        for i in range(n):
            dist[i][i] = 0.0

        # Initialize with direct edges
        for u in graph.nodes():
            u_idx = node_idx[u]
            for v in graph.successors(u):
                v_idx = node_idx[v]
                edge_data = graph[u][v]
                edge_weight = edge_data.get(weight, edge_data.get("distance", 1))
                dist[u_idx][v_idx] = edge_weight
                next_node[u_idx][v_idx] = v

        # Floyd-Warshall main loop
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    if dist[i][k] + dist[k][j] < dist[i][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]
                        next_node[i][j] = next_node[i][k]
                        
                        # Stream progress update for start/end pair
                        if i == node_idx[start] and j == node_idx[end]:
                            await self._stream_visit(
                                websocket,
                                graph,
                                nodes[k],
                                dist[i][j],
                                {"k_index": k, "intermediate_node": nodes[k]},
                            )
                            self._nodes_explored += 1
            
            # Periodically stream frontier updates
            if (k + 1) % max(1, n // 20) == 0:
                await self._stream_frontier(websocket, k + 1)

        time_ms, memory_mb = self._end_tracking()

        start_idx = node_idx[start]
        end_idx = node_idx[end]

        # Check for negative cycles
        if dist[start_idx][start_idx] < 0:
            result = self._no_path_result(time_ms, memory_mb)
            result.error = "Negative cycle detected in graph"
            result.success = False
            return result

        # Check if path exists
        if dist[start_idx][end_idx] == float("inf"):
            return self._no_path_result(time_ms, memory_mb)

        # Reconstruct path
        path = self._reconstruct_path(
            next_node, nodes, start_idx, end_idx, node_idx
        )

        if not path:
            return self._no_path_result(time_ms, memory_mb)

        return self._build_result(
            graph,
            path,
            dist[start_idx][end_idx],
            time_ms,
            memory_mb,
            weight,
            extra={"matrix_size": n, "computation_type": "all-pairs"},
        )

    def _reconstruct_path(
        self, next_node, nodes, start_idx, end_idx, node_idx
    ) -> list[str]:
        """Reconstruct path from next_node matrix."""
        if next_node[start_idx][end_idx] is None:
            return []

        path = [nodes[start_idx]]
        current_idx = start_idx

        # Prevent infinite loops in case of issues
        max_iterations = len(nodes)
        iterations = 0

        while current_idx != end_idx and iterations < max_iterations:
            next_node_id = next_node[current_idx][end_idx]
            if next_node_id is None:
                break
            current_idx = node_idx[next_node_id]
            path.append(nodes[current_idx])
            iterations += 1

        return path if path and path[-1] == nodes[end_idx] else []
