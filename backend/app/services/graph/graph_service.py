"""
Graph Data Service — OSM extraction, graph construction, caching.
Handles osmnx integration, NetworkX graph building, and spatial queries.
"""

import json
import math
import time
import logging
from typing import Optional
from pathlib import Path

import networkx as nx
import numpy as np
import asyncio

try:
    import osmnx as ox
except ImportError:
    ox = None

from app.core.config import settings
from app.core.metrics import metrics

logger = logging.getLogger("pathfinding.graph")

# Speed limit mapping by OSM highway type (km/h)
HIGHWAY_SPEED_MAP = {
    "motorway": settings.SPEED_MOTORWAY,
    "motorway_link": settings.SPEED_MOTORWAY,
    "trunk": settings.SPEED_TRUNK,
    "trunk_link": settings.SPEED_TRUNK,
    "primary": settings.SPEED_PRIMARY,
    "primary_link": settings.SPEED_PRIMARY,
    "secondary": settings.SPEED_SECONDARY,
    "secondary_link": settings.SPEED_SECONDARY,
    "tertiary": settings.SPEED_TERTIARY,
    "tertiary_link": settings.SPEED_TERTIARY,
    "residential": settings.SPEED_RESIDENTIAL,
    "living_street": settings.SPEED_RESIDENTIAL,
    "unclassified": settings.SPEED_UNCLASSIFIED,
    "service": settings.SPEED_SERVICE,
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in meters."""
    R = 6371000  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def parse_maxspeed(maxspeed_value) -> Optional[float]:
    """Parse OSM maxspeed tag value to km/h."""
    if maxspeed_value is None:
        return None
    if isinstance(maxspeed_value, (int, float)):
        return float(maxspeed_value)
    if isinstance(maxspeed_value, list):
        maxspeed_value = maxspeed_value[0]
    s = str(maxspeed_value).strip().lower()
    if s == "none" or s == "signals":
        return 130.0
    if "mph" in s:
        try:
            return float(s.replace("mph", "").strip()) * 1.60934
        except ValueError:
            return None
    try:
        return float(s.replace("km/h", "").replace("kmh", "").strip())
    except ValueError:
        return None


def get_edge_speed(edge_data: dict) -> tuple[float, bool]:
    """
    Get speed for an edge using the fallback hierarchy.
    Returns (speed_kmh, used_fallback).
    """
    # 1. Check maxspeed tag
    maxspeed = parse_maxspeed(edge_data.get("maxspeed"))
    if maxspeed is not None and maxspeed > 0:
        return maxspeed, False

    # 2. Check highway type
    highway = edge_data.get("highway", "")
    if isinstance(highway, list):
        highway = highway[0]
    speed = HIGHWAY_SPEED_MAP.get(highway)
    if speed is not None:
        return float(speed), False

    # 3. Regional default
    return float(settings.SPEED_DEFAULT), True


class GraphService:
    """Service for building and managing road network graphs."""

    def __init__(self):
        self._graph_cache: dict[str, nx.DiGraph] = {}
        self._graph_metadata: dict[str, dict] = {}
        self._cache_dir = Path(settings.GRAPH_CACHE_DIR)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def get_graph_for_region(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float = None,
    ) -> tuple[nx.DiGraph, dict]:
        """
        Get or build a graph for the region around the given coordinates.
        Returns (graph, metadata).
        """
        load_start = time.perf_counter()

        if radius_km is None:
            radius_km = settings.DEFAULT_GRAPH_RADIUS_KM

        cache_key = f"{center_lat:.4f}_{center_lon:.4f}_{radius_km:.4f}"

        if cache_key in self._graph_cache:
            logger.info(f"Graph cache hit: {cache_key}")
            load_time_ms = (time.perf_counter() - load_start) * 1000
            metrics.record_graph_load(load_time_ms, cache_hit=True)
            return self._graph_cache[cache_key], self._graph_metadata[cache_key]

        # Check file cache
        file_path = self._cache_dir / f"{cache_key}.json"
        if file_path.exists():
            logger.info(f"Loading graph from file: {file_path}")
            graph, metadata = self._load_graph_from_file(file_path)
            self._graph_cache[cache_key] = graph
            self._graph_metadata[cache_key] = metadata
            load_time_ms = (time.perf_counter() - load_start) * 1000
            metrics.record_graph_load(load_time_ms, cache_hit=True)
            return graph, metadata

        # Fetch from OSM
        logger.info(
            f"Fetching graph from OSM: center=({center_lat}, {center_lon}), radius={radius_km}km"
        )
        graph, metadata = await self._fetch_and_build_graph(
            center_lat, center_lon, radius_km
        )

        self._graph_cache[cache_key] = graph
        self._graph_metadata[cache_key] = metadata

        # Save to file cache
        self._save_graph_to_file(graph, metadata, file_path)

        load_time_ms = (time.perf_counter() - load_start) * 1000
        metrics.record_graph_load(load_time_ms, cache_hit=False)

        return graph, metadata

    async def get_graph_for_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
    ) -> tuple[nx.DiGraph, dict]:
        """Get or build a graph for the given bounding box."""
        cache_key = f"bbox_{north:.4f}_{south:.4f}_{east:.4f}_{west:.4f}"

        if cache_key in self._graph_cache:
            return self._graph_cache[cache_key], self._graph_metadata[cache_key]

        graph, metadata = await self._fetch_and_build_graph_bbox(
            north, south, east, west
        )
        self._graph_cache[cache_key] = graph
        self._graph_metadata[cache_key] = metadata
        return graph, metadata

    async def _fetch_and_build_graph(
        self, center_lat: float, center_lon: float, radius_km: float
    ) -> tuple[nx.DiGraph, dict]:
        """Fetch OSM data and build a NetworkX graph."""
        radius_m = radius_km * 1000

        if ox is not None:
            try:
                G = await asyncio.to_thread(
                    ox.graph_from_point,
                    (center_lat, center_lon),
                    dist=radius_m,
                    network_type="drive",
                    simplify=True,
                )
                return self._process_osmnx_graph(G)
            except Exception as e:
                logger.warning(f"osmnx fetch failed: {e}, using synthetic graph")

        # Fallback: build a synthetic grid graph for demo/testing
        return self._build_synthetic_graph(center_lat, center_lon, radius_km)

    async def _fetch_and_build_graph_bbox(
        self, north: float, south: float, east: float, west: float
    ) -> tuple[nx.DiGraph, dict]:
        """Fetch OSM data for a bounding box."""
        if ox is not None:
            try:
                G = await asyncio.to_thread(
                    ox.graph_from_bbox,
                    bbox=(north, south, east, west),
                    network_type="drive",
                    simplify=True,
                )
                return self._process_osmnx_graph(G)
            except Exception as e:
                logger.warning(f"osmnx bbox fetch failed: {e}, using synthetic graph")

        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        radius_km = haversine_distance(north, west, south, east) / 2000
        return self._build_synthetic_graph(center_lat, center_lon, radius_km)

    def _process_osmnx_graph(self, G) -> tuple[nx.DiGraph, dict]:
        """Process an osmnx graph into our standard format with computed weights."""
        start_time = time.time()
        fallback_count = 0
        total_edges = 0

        graph = nx.DiGraph()

        # Add nodes with lat/lon
        for node_id, data in G.nodes(data=True):
            graph.add_node(
                str(node_id),
                lat=data.get("y", 0),
                lon=data.get("x", 0),
            )

        # Add edges with computed weights
        for u, v, data in G.edges(data=True):
            total_edges += 1
            u_data = G.nodes[u]
            v_data = G.nodes[v]

            # Distance weight
            distance_m = data.get(
                "length",
                haversine_distance(
                    u_data.get("y", 0),
                    u_data.get("x", 0),
                    v_data.get("y", 0),
                    v_data.get("x", 0),
                ),
            )

            # Time weight with fallback strategy
            speed_kmh, used_fallback = get_edge_speed(data)
            if used_fallback:
                fallback_count += 1
            time_seconds = (
                (distance_m / 1000) / speed_kmh * 3600
                if speed_kmh > 0
                else float("inf")
            )
            geometry_coords = None
            raw_geometry = data.get("geometry")
            if raw_geometry is not None:
                try:
                    geometry_coords = [
                        [float(x), float(y)] for x, y in list(raw_geometry.coords)
                    ]
                except Exception:
                    geometry_coords = None

            graph.add_edge(
                str(u),
                str(v),
                distance=distance_m,
                time=time_seconds,
                speed_kmh=speed_kmh,
                highway=data.get("highway", "unknown"),
                name=data.get("name", ""),
                used_fallback=used_fallback,
                geometry=geometry_coords,
            )

        processing_time = time.time() - start_time
        fallback_pct = fallback_count / total_edges if total_edges > 0 else 0.0

        metadata = {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "fallback_speed_pct": round(fallback_pct, 4),
            "processing_time_ms": round(processing_time * 1000, 2),
            "source": "osm",
        }

        logger.info(
            f"Graph built: {metadata['node_count']} nodes, {metadata['edge_count']} edges, "
            f"{fallback_pct:.1%} fallback speeds, {processing_time:.2f}s"
        )

        return graph, metadata

    def _build_synthetic_graph(
        self, center_lat: float, center_lon: float, radius_km: float
    ) -> tuple[nx.DiGraph, dict]:
        """Build a synthetic grid graph for demo/testing when OSM is unavailable."""
        graph = nx.DiGraph()
        grid_size = min(30, max(10, int(radius_km * 3)))
        lat_step = (radius_km / 111.0) * 2 / grid_size
        lon_step = (
            (radius_km / (111.0 * math.cos(math.radians(center_lat)))) * 2 / grid_size
        )

        start_lat = center_lat - (grid_size / 2) * lat_step
        start_lon = center_lon - (grid_size / 2) * lon_step

        node_grid = {}
        for i in range(grid_size):
            for j in range(grid_size):
                node_id = f"n_{i}_{j}"
                lat = start_lat + i * lat_step
                lon = start_lon + j * lon_step
                graph.add_node(node_id, lat=lat, lon=lon)
                node_grid[(i, j)] = node_id

        # Add edges (4-connected grid with some diagonals)
        import random

        random.seed(42)
        for i in range(grid_size):
            for j in range(grid_size):
                neighbors = []
                if i + 1 < grid_size:
                    neighbors.append((i + 1, j))
                if j + 1 < grid_size:
                    neighbors.append((i, j + 1))
                if i - 1 >= 0:
                    neighbors.append((i - 1, j))
                if j - 1 >= 0:
                    neighbors.append((i, j - 1))
                # Random diagonals
                if random.random() < 0.3:
                    if i + 1 < grid_size and j + 1 < grid_size:
                        neighbors.append((i + 1, j + 1))
                    if i - 1 >= 0 and j - 1 >= 0:
                        neighbors.append((i - 1, j - 1))

                u = node_grid[(i, j)]
                u_data = graph.nodes[u]
                for ni, nj in neighbors:
                    v = node_grid[(ni, nj)]
                    v_data = graph.nodes[v]
                    dist = haversine_distance(
                        u_data["lat"], u_data["lon"], v_data["lat"], v_data["lon"]
                    )
                    speed = random.choice([30, 40, 50, 60]) + random.uniform(-5, 5)
                    time_s = (dist / 1000) / speed * 3600 if speed > 0 else float("inf")
                    graph.add_edge(
                        u,
                        v,
                        distance=dist,
                        time=time_s,
                        speed_kmh=speed,
                        highway="synthetic",
                        name="",
                        used_fallback=False,
                        geometry=[
                            [u_data["lon"], u_data["lat"]],
                            [v_data["lon"], v_data["lat"]],
                        ],
                    )

        metadata = {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "fallback_speed_pct": 0.0,
            "processing_time_ms": 0,
            "source": "synthetic",
        }
        return graph, metadata

    def _save_graph_to_file(self, graph: nx.DiGraph, metadata: dict, file_path: Path):
        """Serialize graph to JSON file."""
        data = {
            "metadata": metadata,
            "nodes": {
                nid: {"lat": d["lat"], "lon": d["lon"]}
                for nid, d in graph.nodes(data=True)
            },
            "edges": [
                {
                    "u": u,
                    "v": v,
                    "distance": d["distance"],
                    "time": d["time"],
                    "speed_kmh": d.get("speed_kmh", 30),
                    "highway": d.get("highway", ""),
                    "name": d.get("name", ""),
                    "geometry": d.get("geometry"),
                }
                for u, v, d in graph.edges(data=True)
            ],
        }
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f)
        logger.info(f"Graph saved to {file_path}")

    def _load_graph_from_file(self, file_path: Path) -> tuple[nx.DiGraph, dict]:
        """Load graph from JSON file."""
        with open(file_path, "r") as f:
            data = json.load(f)

        graph = nx.DiGraph()
        for nid, ndata in data["nodes"].items():
            graph.add_node(nid, **ndata)
        for edge in data["edges"]:
            graph.add_edge(
                edge["u"],
                edge["v"],
                **{k: v for k, v in edge.items() if k not in ("u", "v")},
            )

        return graph, data["metadata"]

    def find_nearest_node(self, graph: nx.DiGraph, lat: float, lon: float) -> str:
        """Find the nearest node in the graph to the given coordinates."""
        min_dist = float("inf")
        nearest = None
        for nid, data in graph.nodes(data=True):
            d = haversine_distance(lat, lon, data["lat"], data["lon"])
            if d < min_dist:
                min_dist = d
                nearest = nid
        return nearest

    def shortest_path_hops(self, graph: nx.DiGraph, start: str, end: str) -> list[str]:
        """Compute an unweighted path for endpoint-aware subgraph extraction."""
        try:
            return nx.shortest_path(graph, source=start, target=end)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_endpoint_subgraph(
        self, graph: nx.DiGraph, start: str, end: str, max_nodes: int
    ) -> tuple[nx.DiGraph, dict]:
        """
        Build a Floyd-safe subgraph that always contains start/end and path corridor.
        Returns (subgraph, metadata).
        """
        if graph.number_of_nodes() <= max_nodes:
            return graph, {"used_subgraph": False, "node_limit": max_nodes}

        if start not in graph or end not in graph:
            raise ValueError("Start or end node is not present in graph")

        path_nodes = self.shortest_path_hops(graph, start, end)
        selected = set(path_nodes[:max_nodes])
        frontier = set(path_nodes[:max_nodes])

        if start not in selected:
            selected.add(start)
            frontier.add(start)
        if end not in selected and len(selected) < max_nodes:
            selected.add(end)
            frontier.add(end)

        while len(selected) < max_nodes and frontier:
            current = frontier.pop()
            neighbors = list(graph.successors(current)) + list(
                graph.predecessors(current)
            )
            for neighbor in neighbors:
                if neighbor in selected:
                    continue
                selected.add(neighbor)
                frontier.add(neighbor)
                if len(selected) >= max_nodes:
                    break

        if start not in selected or end not in selected:
            raise ValueError(
                "Unable to build endpoint-aware Floyd-Warshall subgraph under node limit"
            )

        return graph.subgraph(selected).copy(), {
            "used_subgraph": True,
            "node_limit": max_nodes,
            "selected_nodes": len(selected),
            "full_nodes": graph.number_of_nodes(),
            "path_seed_nodes": len(path_nodes),
        }

    def get_subgraph(self, graph: nx.DiGraph, max_nodes: int) -> nx.DiGraph:
        """Get a subgraph with at most max_nodes nodes (for Floyd-Warshall)."""
        if graph.number_of_nodes() <= max_nodes:
            return graph
        nodes = list(graph.nodes())[:max_nodes]
        return graph.subgraph(nodes).copy()

    def get_graph_stats(self, graph: nx.DiGraph) -> dict:
        """Get statistics about a graph."""
        return {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "is_strongly_connected": nx.is_strongly_connected(graph)
            if graph.number_of_nodes() < 10000
            else None,
            "density": nx.density(graph),
        }


# Singleton
graph_service = GraphService()
