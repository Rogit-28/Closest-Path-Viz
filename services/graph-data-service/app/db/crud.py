from sqlalchemy.orm import Session
from app.db import models
from networkx.readwrite import json_graph
from shapely.geometry import box
import networkx as nx

def get_graph_by_place_name(db: Session, place_name: str):
    """
    Retrieves a graph by its place name.
    """
    return db.query(models.Graph).filter(models.Graph.place_name == place_name).first()

def create_graph(db: Session, place_name: str, graph: nx.DiGraph):
    """
    Saves a graph to the database.
    """
    graph_data = json_graph.adjacency_data(graph)

    # Get the bounding box of the graph
    nodes = graph.nodes(data=True)
    min_lon = min(node[1]['x'] for node in nodes)
    min_lat = min(node[1]['y'] for node in nodes)
    max_lon = max(node[1]['x'] for node in nodes)
    max_lat = max(node[1]['y'] for node in nodes)

    bounding_box = box(min_lon, min_lat, max_lon, max_lat)

    db_graph = models.Graph(
        place_name=place_name,
        graph_data=graph_data,
        bounding_box=f'SRID=4326;{bounding_box.wkt}'
    )
    db.add(db_graph)
    db.commit()
    db.refresh(db_graph)
    return db_graph
