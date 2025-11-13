import heapq
import networkx as nx
from app.core.pathfinding import PathfindingAlgorithm

class Dijkstra(PathfindingAlgorithm):
    async def find_path(self, graph: nx.DiGraph, start_node: int, end_node: int, websocket):
        distances = {node: float('infinity') for node in graph.nodes}
        distances[start_node] = 0
        priority_queue = [(0, start_node)]
        previous_nodes = {node: None for node in graph.nodes}

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_distance > distances[current_node]:
                continue

            if current_node == end_node:
                break

            await self.stream_node_visit(websocket, current_node, current_distance, {})

            for neighbor in graph.neighbors(current_node):
                weight = graph[current_node][neighbor].get('length', 1)
                distance = current_distance + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous_nodes[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))

        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = previous_nodes[current]

        return path[::-1], distances[end_node]
