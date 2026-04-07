"""Contract and serialization regression tests."""

from __future__ import annotations

import networkx as nx
import pytest

from app.schemas.pathfinding import AlgorithmType, PathfindingConfig
from app.services.pathfinding.base import PathResult
from app.services.pathfinding.dijkstra import DijkstraPathfinder
from app.services.pathfinding.engine import run_pathfinding
from app.services.pathfinding.serialization import (
    finite_or_none,
    sanitize_for_json,
    serialize_result_payload,
)


@pytest.fixture
def small_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node("A", lat=0.0, lon=0.0)
    g.add_node("B", lat=0.5, lon=0.5)
    g.add_node("C", lat=1.0, lon=1.0)
    g.add_node("D", lat=1.5, lon=1.5)

    # Primary path A -> B -> D
    g.add_edge("A", "B", distance=1.0, time=1.0)
    g.add_edge("B", "D", distance=1.0, time=1.0)

    # Alternative path A -> C -> D
    g.add_edge("A", "C", distance=1.4, time=1.4)
    g.add_edge("C", "D", distance=1.0, time=1.0)
    return g


def test_finite_or_none_rejects_non_finite() -> None:
    assert finite_or_none(float("inf")) is None
    assert finite_or_none(float("-inf")) is None
    assert finite_or_none(float("nan")) is None
    assert finite_or_none(1.23456) == 1.2346


def test_sanitize_for_json_normalizes_nested_non_finite() -> None:
    payload = {
        "a": float("inf"),
        "b": [1.0, float("nan"), {"x": float("-inf")}],
        "c": "ok",
    }
    sanitized = sanitize_for_json(payload)
    assert sanitized["a"] is None
    assert sanitized["b"][1] is None
    assert sanitized["b"][2]["x"] is None
    assert sanitized["c"] == "ok"


def test_serialize_result_payload_sets_null_cost_and_identity() -> None:
    result = PathResult(
        algorithm="yens_k_shortest",
        path=[],
        path_coords=[],
        path_geometry=[],
        cost=float("nan"),
        nodes_explored=17,
        computation_time_ms=12.34,
        memory_usage_mb=1.23,
        path_length_km=0.0,
        extra={"reason": "no_path"},
        success=False,
        error="No path found between start and end nodes.",
    )

    payload = serialize_result_payload(
        result,
        requested_algorithm="dijkstra",
        executed_algorithm="yens_k_shortest",
    )

    assert payload["algorithm"] == "dijkstra"
    assert payload["requested_algorithm"] == "dijkstra"
    assert payload["executed_algorithm"] == "yens_k_shortest"
    assert payload["metrics"]["cost"] is None
    assert payload["metrics"]["extra"]["requested_algorithm"] == "dijkstra"
    assert payload["metrics"]["extra"]["executed_algorithm"] == "yens_k_shortest"


@pytest.mark.asyncio
async def test_run_pathfinding_kpaths_preserves_requested_identity(
    small_graph: nx.DiGraph,
) -> None:
    config = PathfindingConfig(k_paths=2)
    result = await run_pathfinding(
        small_graph,
        "A",
        "D",
        AlgorithmType.DIJKSTRA,
        config,
    )

    assert result.extra["requested_algorithm"] == "dijkstra"
    assert result.extra["executed_algorithm"] == "yens_k_shortest"


def test_event_buffer_is_hard_capped_and_reports_drops() -> None:
    algo = DijkstraPathfinder()
    algo._max_event_buffer = 3

    for i in range(10):
        algo._append_event({"type": "node_visit", "i": i})

    assert len(algo._event_buffer) == 3
    assert algo._dropped_event_count == 7

    no_path = algo._no_path_result(time_ms=1.0, memory_mb=1.0)
    assert no_path.extra["dropped_events"] == 7
