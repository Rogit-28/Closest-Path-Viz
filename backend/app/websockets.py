"""
WebSocket handlers for real-time pathfinding visualization.

Streams node visits and algorithm progress to connected clients.
Uses GraphService to load real road-network graphs.
"""

import json
import asyncio
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.services.pathfinding.engine import run_pathfinding, run_multi_pathfinding
from app.services.graph.graph_service import graph_service
from app.schemas.pathfinding import (
    AlgorithmType,
    PathfindingConfig,
    HeuristicType,
    WeightFunction,
)

logger = logging.getLogger("pathfinding.ws")


class ConnectionManager:
    """Manager for WebSocket connections and broadcasting."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_personal(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, message: dict):
        disconnected = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)


manager = ConnectionManager()


async def pathfinding_websocket_handler(websocket: WebSocket, client_id: str):
    """
    Handle WebSocket connection for real-time pathfinding visualization.

    Client sends a JSON message:
    {
        "start": {"lat": ..., "lon": ...},
        "end": {"lat": ..., "lon": ...},
        "algorithms": ["dijkstra", "astar", ...],
        "config": { ... }
    }

    Server streams back:
    - graph_info: metadata about loaded graph
    - algorithm_start: when each algorithm begins
    - node_visit: each explored node
    - frontier_update: frontier size changes
    - complete: when each algorithm finishes with path + metrics
    - all_complete: when all algorithms are done
    - error: on failure
    """
    await manager.connect(websocket, client_id)

    try:
        # Wait for the pathfinding request
        raw = await websocket.receive_text()
        request = json.loads(raw)

        start_coord = request.get("start", {})
        end_coord = request.get("end", {})
        algorithm_names = request.get("algorithms", ["astar"])
        config_data = request.get("config", {})

        start_lat = start_coord.get("lat", 0)
        start_lon = start_coord.get("lon", 0)
        end_lat = end_coord.get("lat", 0)
        end_lon = end_coord.get("lon", 0)

        # Build PathfindingConfig from request
        config = PathfindingConfig(
            astar_heuristic=HeuristicType(
                config_data.get("astar_heuristic", "haversine")
            ),
            weight_function=WeightFunction(
                config_data.get("weight_function", "distance")
            ),
            k_paths=config_data.get("k_paths", 1),
            animation_speed=config_data.get("animation_speed", 1.0),
            show_all_explored=config_data.get("show_all_explored", True),
            animation_granularity=config_data.get(
                "animation_granularity", "every_node"
            ),
        )

        # Load the graph for the region between start and end
        center_lat = (start_lat + end_lat) / 2
        center_lon = (start_lon + end_lon) / 2

        try:
            graph, metadata = await graph_service.get_graph_for_region(
                center_lat, center_lon
            )
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            await manager.send_personal(
                {"type": "error", "message": f"Failed to load graph: {str(e)}"},
                client_id,
            )
            return

        # Send graph info
        await manager.send_personal(
            {
                "type": "graph_info",
                "metadata": metadata,
            },
            client_id,
        )

        # Find nearest nodes to start and end coordinates
        start_node = graph_service.find_nearest_node(graph, start_lat, start_lon)
        end_node = graph_service.find_nearest_node(graph, end_lat, end_lon)

        if start_node is None or end_node is None:
            await manager.send_personal(
                {
                    "type": "error",
                    "message": "Could not find nodes near the specified coordinates",
                },
                client_id,
            )
            return

        if start_node == end_node:
            await manager.send_personal(
                {
                    "type": "error",
                    "message": "Start and end resolve to the same node. Try further apart points.",
                },
                client_id,
            )
            return

        # Run each algorithm sequentially
        for algo_name in algorithm_names:
            try:
                algo_type = AlgorithmType(algo_name)
            except ValueError:
                await manager.send_personal(
                    {"type": "error", "message": f"Unknown algorithm: {algo_name}"},
                    client_id,
                )
                continue

            # Send algorithm_start
            await manager.send_personal(
                {"type": "algorithm_start", "algorithm": algo_name},
                client_id,
            )

            # For Floyd-Warshall, use a subgraph if too large
            run_graph = graph
            if algo_type == AlgorithmType.FLOYD_WARSHALL:
                from app.core.config import settings

                run_graph = graph_service.get_subgraph(
                    graph, settings.FLOYD_WARSHALL_NODE_LIMIT
                )

            try:
                result = await run_pathfinding(
                    run_graph,
                    start_node,
                    end_node,
                    algo_type,
                    config,
                    websocket=websocket,
                )

                # The engine already sends the 'complete' message via websocket
                # But we add path_nodes for the frontend to draw
                if not result.success:
                    await manager.send_personal(
                        {
                            "type": "complete",
                            "algorithm": algo_name,
                            "path": [],
                            "metrics": {
                                "nodes_explored": result.nodes_explored,
                                "path_length_km": 0,
                                "computation_time_ms": result.computation_time_ms,
                                "memory_usage_mb": result.memory_usage_mb,
                                "cost": 0,
                                "path_node_count": 0,
                                "extra": {},
                            },
                            "success": False,
                            "error": result.error,
                        },
                        client_id,
                    )

            except Exception as e:
                logger.error(f"Algorithm {algo_name} failed: {e}")
                await manager.send_personal(
                    {
                        "type": "complete",
                        "algorithm": algo_name,
                        "path": [],
                        "metrics": {
                            "nodes_explored": 0,
                            "path_length_km": 0,
                            "computation_time_ms": 0,
                            "memory_usage_mb": 0,
                            "cost": 0,
                            "path_node_count": 0,
                            "extra": {},
                        },
                        "success": False,
                        "error": str(e),
                    },
                    client_id,
                )

        # Signal that all algorithms are done
        await manager.send_personal(
            {"type": "all_complete"},
            client_id,
        )

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from client {client_id}: {e}")
        try:
            await manager.send_personal(
                {"type": "error", "message": "Invalid JSON request"},
                client_id,
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        try:
            await manager.send_personal(
                {"type": "error", "message": f"Server error: {str(e)}"},
                client_id,
            )
        except Exception:
            pass
    finally:
        manager.disconnect(client_id)
