import os
import requests
import networkx as nx
from fastapi import APIRouter
from networkx.readwrite import json_graph
from app.core.dijkstra import Dijkstra
from app.core.astar import AStar

router = APIRouter()

GRAPH_DATA_SERVICE_URL = os.environ.get("GRAPH_DATA_SERVICE_URL")

def get_graph_from_service(place_name: str):
    response = requests.get(f"{GRAPH_DATA_SERVICE_URL}/graphs/{place_name}")
    if response.status_code == 200:
        graph_data = response.json()["graph_data"]
        return json_graph.adjacency_graph(graph_data)
    return None

@router.post("/route")
async def find_route(place_name: str, start_node: int, end_node: int, algorithm: str, astar_heuristic: str = "haversine"):
    graph = get_graph_from_service(place_name)
    if graph is None:
        return {"error": "Graph not found"}

    if algorithm == "dijkstra":
        pathfinder = Dijkstra()
    elif algorithm == "astar":
        pathfinder = AStar(heuristic_type=astar_heuristic)
    else:
        return {"error": "Invalid algorithm"}

    # We will pass a dummy websocket for now.
    # The actual websocket connection will be handled in the next step.
    path, cost = await pathfinder.find_path(graph, start_node, end_node, None)

    return {"path": path, "cost": cost}
