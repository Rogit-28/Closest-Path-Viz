import osmnx as ox
import networkx as nx

def create_graph_from_osm(place_name: str) -> nx.DiGraph:
    """
    Fetches road network data from OpenStreetMap for a given place and
    creates a directed graph.

    Args:
        place_name: The name of the place to fetch data for (e.g., "Manhattan, New York").

    Returns:
        A NetworkX DiGraph representing the road network.
    """
    # G_proj is the projected graph, which is suitable for most analyses.
    # We use the unprojected graph G for saving to PostGIS, as PostGIS
    # works with lat/lon coordinates.
    G = ox.graph_from_place(place_name, network_type="drive")

    # osmnx automatically adds edge lengths in meters.
    # We can add other attributes like travel time if speed data is available.

    return G
