"""
Serialization helpers for pathfinding payloads.

Ensures all API/stream payloads are JSON-safe (no NaN/Infinity) and keeps
cross-interface field shapes consistent.
"""

from __future__ import annotations

import math
from typing import Any


def finite_or_none(value: Any, *, digits: int = 4) -> float | None:
    """Return a rounded finite float or None when value is not finite."""
    if value is None:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(as_float):
        return None
    return round(as_float, digits)


def sanitize_for_json(value: Any) -> Any:
    """
    Recursively sanitize values to guarantee JSON-compliant numbers.

    Non-finite numbers are converted to None.
    """
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int,)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_json(v) for v in value]
    return value


def serialize_result_payload(
    result,
    *,
    requested_algorithm: str | None = None,
    executed_algorithm: str | None = None,
) -> dict[str, Any]:
    """
    Build a JSON-safe result payload for REST/SSE/WebSocket completion messages.
    """
    requested_algo = requested_algorithm or result.algorithm
    executed_algo = executed_algorithm or result.algorithm

    raw_extra = dict(result.extra or {})
    raw_extra.setdefault("requested_algorithm", requested_algo)
    raw_extra.setdefault("executed_algorithm", executed_algo)

    return {
        "algorithm": requested_algo,
        "requested_algorithm": requested_algo,
        "executed_algorithm": executed_algo,
        "path": result.path_coords,
        "path_geometry": result.path_geometry,
        "metrics": {
            "nodes_explored": int(result.nodes_explored),
            "path_length_km": finite_or_none(result.path_length_km),
            "computation_time_ms": finite_or_none(result.computation_time_ms, digits=2),
            "memory_usage_mb": finite_or_none(result.memory_usage_mb, digits=4),
            "cost": finite_or_none(result.cost),
            "path_node_count": len(result.path),
            "extra": sanitize_for_json(raw_extra),
        },
        "success": bool(result.success),
        "error": result.error,
    }

