import heapq
import networkx as nx
from app.core.pathfinding import PathfindingAlgorithm
import math

class AStar(PathfindingAlgorithm):
    def __init__(self, heuristic_type: str):
        self.heuristic = {
            "haversine": self._haversine,
            "manhattan": self._manhattan,
            "euclidean": self._euclidean,
            "zero": lambda a, b, graph: 0
        }[heuristic_type]

    def _haversine(self, node1, node2, graph):
        lat1, lon1 = graph.nodes[node1]['y'], graph.nodes[node1]['x']
        lat2, lon2 = graph.nodes[node2]['y'], graph.nodes[node2]['x']
        R = 6371  # Earth radius in kilometers
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance * 1000 # convert to meters

    def _manhattan(self, node1, node2, graph):
        lat1, lon1 = graph.nodes[node1]['y'], graph.nodes[node1]['x']
        lat2, lon2 = graph.nodes[node2]['y'], graph.nodes[node2]['x']
        return abs(lat1 - lat2) + abs(lon1 - lon2)

    def _euclidean(self, node1, node2, graph):
        lat1, lon1 = graph.nodes[node1]['y'], graph.nodes[node1]['x']
        lat2, lon2 = graph.nodes[node2]['y'], graph.nodes[node2]['x']
        return math.sqrt((lat1-lat2)**2 + (lon1-lon2)**2)


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
                distance = distances[current_node] + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous_nodes[neighbor] = current_node
                    priority = distance + self.heuristic(neighbor, end_node, graph)
                    heapq.heappush(priority_queue, (priority, neighbor))

        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = previous_nodes[current]

        return path[::-1], distances[end_node]
