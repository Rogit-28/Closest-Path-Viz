"""
In-memory metrics collector for performance monitoring.
Thread-safe singleton that tracks application performance metrics.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


@dataclass
class MetricsCollector:
    """
    Collects and stores performance metrics in memory.
    Uses rolling windows (deque) to avoid unbounded memory growth.
    """

    # Rolling window size for time series data
    WINDOW_SIZE: int = 100

    # Startup metrics
    startup_time_ms: float = 0.0
    startup_timestamp: float = 0.0
    db_connected: bool = False
    redis_connected: bool = False

    # Graph loading metrics
    graph_loads_total: int = 0
    graph_cache_hits: int = 0
    graph_cache_misses: int = 0
    graph_load_times_ms: deque = field(default_factory=lambda: deque(maxlen=100))

    # Algorithm metrics (per algorithm type)
    algorithm_runs: dict = field(default_factory=dict)
    algorithm_times_ms: dict = field(default_factory=dict)

    # SSE connection metrics
    sse_connections_total: int = 0
    sse_active_connections: int = 0
    sse_connection_times_ms: deque = field(default_factory=lambda: deque(maxlen=100))

    # Request metrics
    requests_total: int = 0
    requests_active: int = 0

    # Lock for thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_startup(
        self, startup_time_ms: float, db_ok: bool = False, redis_ok: bool = False
    ):
        """Record application startup metrics."""
        with self._lock:
            self.startup_time_ms = startup_time_ms
            self.startup_timestamp = time.time()
            self.db_connected = db_ok
            self.redis_connected = redis_ok

    def record_graph_load(self, time_ms: float, cache_hit: bool):
        """Record a graph load operation."""
        with self._lock:
            self.graph_loads_total += 1
            if cache_hit:
                self.graph_cache_hits += 1
            else:
                self.graph_cache_misses += 1
            self.graph_load_times_ms.append(time_ms)

    def record_algorithm_run(self, algorithm: str, time_ms: float):
        """Record an algorithm execution."""
        with self._lock:
            if algorithm not in self.algorithm_runs:
                self.algorithm_runs[algorithm] = 0
                self.algorithm_times_ms[algorithm] = deque(maxlen=self.WINDOW_SIZE)

            self.algorithm_runs[algorithm] += 1
            self.algorithm_times_ms[algorithm].append(time_ms)

    def record_sse_connect(self, connect_time_ms: float):
        """Record an SSE connection establishment."""
        with self._lock:
            self.sse_connections_total += 1
            self.sse_connection_times_ms.append(connect_time_ms)

    def increment_sse_active(self):
        """Increment active SSE connection count."""
        with self._lock:
            self.sse_active_connections += 1

    def decrement_sse_active(self):
        """Decrement active SSE connection count."""
        with self._lock:
            self.sse_active_connections = max(0, self.sse_active_connections - 1)

    def increment_requests(self):
        """Increment request counters."""
        with self._lock:
            self.requests_total += 1
            self.requests_active += 1

    def decrement_active_requests(self):
        """Decrement active request count."""
        with self._lock:
            self.requests_active = max(0, self.requests_active - 1)

    def _calculate_stats(self, times: deque) -> dict:
        """Calculate avg, p95, and last value from a deque of times."""
        if not times:
            return {"avg_ms": 0, "p95_ms": 0, "last_ms": 0}

        times_list = list(times)
        avg_ms = sum(times_list) / len(times_list)

        # P95 calculation
        sorted_times = sorted(times_list)
        p95_idx = int(len(sorted_times) * 0.95)
        p95_ms = sorted_times[min(p95_idx, len(sorted_times) - 1)]

        return {
            "avg_ms": round(avg_ms, 2),
            "p95_ms": round(p95_ms, 2),
            "last_ms": round(times_list[-1], 2) if times_list else 0,
        }

    def get_metrics(self) -> dict:
        """Get all metrics as a dictionary."""
        with self._lock:
            now = time.time()
            uptime = now - self.startup_timestamp if self.startup_timestamp > 0 else 0

            # Graph stats
            graph_stats = self._calculate_stats(self.graph_load_times_ms)
            cache_hit_rate = (
                (self.graph_cache_hits / self.graph_loads_total * 100)
                if self.graph_loads_total > 0
                else 0
            )

            # Algorithm stats
            algorithms = {}
            for algo, runs in self.algorithm_runs.items():
                times = self.algorithm_times_ms.get(algo, deque())
                stats = self._calculate_stats(times)
                algorithms[algo] = {"runs": runs, **stats}

            # SSE stats
            sse_stats = self._calculate_stats(self.sse_connection_times_ms)

            return {
                "startup": {
                    "time_ms": round(self.startup_time_ms, 2),
                    "timestamp": self.startup_timestamp,
                    "uptime_seconds": round(uptime, 1),
                    "db_connected": self.db_connected,
                    "redis_connected": self.redis_connected,
                },
                "graph": {
                    "loads_total": self.graph_loads_total,
                    "cache_hits": self.graph_cache_hits,
                    "cache_misses": self.graph_cache_misses,
                    "cache_hit_rate_pct": round(cache_hit_rate, 1),
                    **graph_stats,
                },
                "algorithms": algorithms,
                "sse": {
                    "connections_total": self.sse_connections_total,
                    "active_connections": self.sse_active_connections,
                    **sse_stats,
                },
                "requests": {
                    "total": self.requests_total,
                    "active": self.requests_active,
                },
            }

    def reset(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.startup_time_ms = 0.0
            self.startup_timestamp = 0.0
            self.db_connected = False
            self.redis_connected = False
            self.graph_loads_total = 0
            self.graph_cache_hits = 0
            self.graph_cache_misses = 0
            self.graph_load_times_ms.clear()
            self.algorithm_runs.clear()
            self.algorithm_times_ms.clear()
            self.sse_connections_total = 0
            self.sse_active_connections = 0
            self.sse_connection_times_ms.clear()
            self.requests_total = 0
            self.requests_active = 0


# Singleton instance
metrics = MetricsCollector()
