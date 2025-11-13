from abc import ABC, abstractmethod
import networkx as nx

class PathfindingAlgorithm(ABC):
    @abstractmethod
    async def find_path(self, graph: nx.DiGraph, start_node: int, end_node: int, websocket):
        pass

    async def stream_node_visit(self, websocket, node_id, cost, metadata):
        await websocket.send_json({
            "type": "node_visit",
            "node": node_id,
            "cost": cost,
            "metadata": metadata
        })
