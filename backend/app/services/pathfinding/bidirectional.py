"""
Bidirectional Dijkstra — simultaneous forward/backward search.
"""

import heapq

import networkx as nx

from app.services.pathfinding.base import PathfindingAlgorithm, PathResult


class BidirectionalDijkstraPathfinder(PathfindingAlgorithm):
    def __init__(self):
        super().__init__("bidirectional")

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

        self._begin_tracking(config)

        # Build reverse graph for backward search
        reverse_graph = graph.reverse(copy=False)

        # Forward search structures
        fwd_pq = [(0.0, start)]
        fwd_dist = {start: 0.0}
        fwd_prev = {}
        fwd_visited = set()

        # Backward search structures
        bwd_pq = [(0.0, end)]
        bwd_dist = {end: 0.0}
        bwd_prev = {}
        bwd_visited = set()
        hybrid_resolver = (config or {}).get("hybrid_resolver")

        best_cost = float("inf")
        meeting_node = None

        while fwd_pq or bwd_pq:
            # Forward step
            if fwd_pq:
                fwd_cost, fwd_node = heapq.heappop(fwd_pq)

                if fwd_node not in fwd_visited:
                    fwd_visited.add(fwd_node)
                    await self._stream_visit(
                        websocket,
                        graph,
                        fwd_node,
                        fwd_cost,
                        {"direction": "forward"},
                    )

                    # Check if backward search reached this node
                    if fwd_node in bwd_visited:
                        total = fwd_dist[fwd_node] + bwd_dist[fwd_node]
                        if total < best_cost:
                            best_cost = total
                            meeting_node = fwd_node

                    for neighbor in graph.successors(fwd_node):
                        if neighbor in fwd_visited:
                            continue
                        edge_data = graph[fwd_node][neighbor]
                        if weight == "hybrid" and hybrid_resolver is not None:
                            edge_w = hybrid_resolver(edge_data)
                        else:
                            edge_w = edge_data.get(weight, edge_data.get("distance", 1))
                        new_cost = fwd_cost + edge_w
                        is_improved = new_cost < fwd_dist.get(neighbor, float("inf"))
                        await self._stream_edge(
                            websocket,
                            graph,
                            fwd_node,
                            neighbor,
                            new_cost,
                            {
                                "direction": "forward",
                                "edge_weight": round(edge_w, 4),
                                "candidate": True,
                                "improved": is_improved,
                            },
                        )
                        if is_improved:
                            fwd_dist[neighbor] = new_cost
                            fwd_prev[neighbor] = fwd_node
                            heapq.heappush(fwd_pq, (new_cost, neighbor))

            # Backward step
            if bwd_pq:
                bwd_cost, bwd_node = heapq.heappop(bwd_pq)

                if bwd_node not in bwd_visited:
                    bwd_visited.add(bwd_node)
                    await self._stream_visit(
                        websocket,
                        graph,
                        bwd_node,
                        bwd_cost,
                        {"direction": "backward"},
                    )

                    if bwd_node in fwd_visited:
                        total = fwd_dist[bwd_node] + bwd_dist[bwd_node]
                        if total < best_cost:
                            best_cost = total
                            meeting_node = bwd_node

                    for neighbor in reverse_graph.successors(bwd_node):
                        if neighbor in bwd_visited:
                            continue
                        edge_data = reverse_graph[bwd_node][neighbor]
                        if weight == "hybrid" and hybrid_resolver is not None:
                            edge_w = hybrid_resolver(edge_data)
                        else:
                            edge_w = edge_data.get(weight, edge_data.get("distance", 1))
                        new_cost = bwd_cost + edge_w
                        is_improved = new_cost < bwd_dist.get(neighbor, float("inf"))
                        await self._stream_edge(
                            websocket,
                            graph,
                            neighbor,
                            bwd_node,
                            new_cost,
                            {
                                "direction": "backward",
                                "edge_weight": round(edge_w, 4),
                                "candidate": True,
                                "improved": is_improved,
                            },
                        )
                        if is_improved:
                            bwd_dist[neighbor] = new_cost
                            bwd_prev[neighbor] = bwd_node
                            heapq.heappush(bwd_pq, (new_cost, neighbor))

            # Termination check
            fwd_min = fwd_pq[0][0] if fwd_pq else float("inf")
            bwd_min = bwd_pq[0][0] if bwd_pq else float("inf")
            if fwd_min + bwd_min >= best_cost:
                break

            if self._nodes_explored % 50 == 0:
                await self._stream_frontier(websocket, len(fwd_pq) + len(bwd_pq))

        time_ms, memory_mb = self._end_tracking()

        if meeting_node is None:
            return self._no_path_result(time_ms, memory_mb)

        # Reconstruct path through meeting point
        fwd_path = self._reconstruct_forward(fwd_prev, start, meeting_node)
        bwd_path = self._reconstruct_backward(bwd_prev, end, meeting_node)
        full_path = fwd_path + bwd_path[1:]  # avoid duplicating meeting node

        return self._build_result(
            graph,
            full_path,
            best_cost,
            time_ms,
            memory_mb,
            weight,
            extra={"meeting_node": meeting_node},
        )

    def _reconstruct_forward(self, prev: dict, start: str, meeting: str) -> list[str]:
        path = []
        current = meeting
        while current is not None:
            path.append(current)
            current = prev.get(current)
        path.reverse()
        return path if path and path[0] == start else []

    def _reconstruct_backward(self, prev: dict, end: str, meeting: str) -> list[str]:
        path = []
        current = meeting
        while current is not None:
            path.append(current)
            current = prev.get(current)
        return path if path and path[-1] == end else []
