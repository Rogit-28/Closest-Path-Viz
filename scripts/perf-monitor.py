#!/usr/bin/env python3
"""
Pathfinder Performance Monitor - Live CLI Dashboard

A real-time terminal dashboard for monitoring Docker containers and
application performance metrics.

Usage:
    python perf-monitor.py [OPTIONS]

Options:
    --refresh, -r   Refresh interval in seconds (default: 1)
    --logs, -l      Show log tail panel
    --api-url       Backend API URL (default: http://localhost:8000)

Press 'q' to quit, 'l' to toggle logs, 'r' to refresh immediately.
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

try:
    import docker
    from docker.errors import DockerException
except ImportError:
    print("Error: docker package not installed. Run: pip install docker")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("Error: httpx package not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.style import Style
    from rich import box
except ImportError:
    print("Error: rich package not installed. Run: pip install rich")
    sys.exit(1)


# Container name patterns to monitor
CONTAINER_PATTERNS = ["closest_path_api", "closest_path_web", "closest_path"]

console = Console()


def format_bytes(b: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(b) < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"


def format_duration(seconds: float) -> str:
    """Format duration to human readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_uptime(seconds: float) -> str:
    """Format uptime to human readable string."""
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


class DockerMonitor:
    """Monitors Docker containers."""

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.connected = True
        except DockerException as e:
            console.print(f"[red]Warning: Could not connect to Docker: {e}[/red]")
            self.client = None
            self.connected = False

    def get_containers(self) -> list[dict]:
        """Get information about monitored containers."""
        if not self.connected or self.client is None:
            return []

        containers = []
        try:
            for container in self.client.containers.list(all=True):
                name = container.name
                # Check if this container matches our patterns
                if not any(pattern in name for pattern in CONTAINER_PATTERNS):
                    continue

                status = container.status
                created = container.attrs.get("Created", "")
                started = container.attrs.get("State", {}).get("StartedAt", "")

                # Calculate uptime
                uptime_seconds = 0
                if status == "running" and started:
                    try:
                        # Parse ISO format timestamp
                        start_time = datetime.fromisoformat(
                            started.replace("Z", "+00:00")
                        )
                        uptime_seconds = (
                            datetime.now(start_time.tzinfo) - start_time
                        ).total_seconds()
                    except Exception:
                        pass

                # Get stats if running
                cpu_percent = 0.0
                memory_usage = 0
                memory_limit = 0
                net_rx = 0
                net_tx = 0

                if status == "running":
                    try:
                        stats = container.stats(stream=False)

                        # CPU calculation
                        cpu_delta = (
                            stats["cpu_stats"]["cpu_usage"]["total_usage"]
                            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
                        )
                        system_delta = (
                            stats["cpu_stats"]["system_cpu_usage"]
                            - stats["precpu_stats"]["system_cpu_usage"]
                        )
                        cpu_count = stats["cpu_stats"].get("online_cpus", 1)
                        if system_delta > 0:
                            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100

                        # Memory
                        memory_usage = stats["memory_stats"].get("usage", 0)
                        memory_limit = stats["memory_stats"].get("limit", 0)

                        # Network
                        networks = stats.get("networks", {})
                        for iface_stats in networks.values():
                            net_rx += iface_stats.get("rx_bytes", 0)
                            net_tx += iface_stats.get("tx_bytes", 0)
                    except Exception:
                        pass

                containers.append(
                    {
                        "name": name,
                        "status": status,
                        "uptime_seconds": uptime_seconds,
                        "cpu_percent": cpu_percent,
                        "memory_usage": memory_usage,
                        "memory_limit": memory_limit,
                        "net_rx": net_rx,
                        "net_tx": net_tx,
                    }
                )
        except Exception as e:
            console.print(f"[red]Error getting containers: {e}[/red]")

        return containers

    def get_logs(self, container_name: str, tail: int = 15) -> list[str]:
        """Get recent logs from a container."""
        if not self.connected or self.client is None:
            return []

        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True).decode(
                "utf-8", errors="replace"
            )
            return logs.strip().split("\n") if logs.strip() else []
        except Exception:
            return []


class MetricsClient:
    """Fetches metrics from the backend API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=5.0)
        self.last_metrics: Optional[dict] = None
        self.last_error: Optional[str] = None

    async def fetch_metrics(self) -> Optional[dict]:
        """Fetch metrics from /metrics endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/metrics")
            if response.status_code == 200:
                self.last_metrics = response.json()
                self.last_error = None
                return self.last_metrics
            else:
                self.last_error = f"HTTP {response.status_code}"
                return None
        except httpx.ConnectError:
            self.last_error = "Connection refused"
            return None
        except httpx.TimeoutException:
            self.last_error = "Timeout"
            return None
        except Exception as e:
            self.last_error = str(e)
            return None

    async def health_check(self) -> tuple[bool, float]:
        """Check /health endpoint and return (ok, latency_ms)."""
        try:
            start = time.perf_counter()
            response = await self.client.get(f"{self.base_url}/health")
            latency_ms = (time.perf_counter() - start) * 1000
            return response.status_code == 200, latency_ms
        except Exception:
            return False, 0.0

    async def close(self):
        await self.client.aclose()


class Dashboard:
    """Renders the live terminal dashboard."""

    def __init__(
        self,
        refresh_interval: float = 1.0,
        show_logs: bool = False,
        api_url: str = "http://localhost:8000",
    ):
        self.refresh_interval = refresh_interval
        self.show_logs = show_logs
        self.docker_monitor = DockerMonitor()
        self.metrics_client = MetricsClient(api_url)
        self.running = True
        self.last_update = time.time()

    def create_header(self) -> Panel:
        """Create header panel."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header_text = Text()
        header_text.append("PATHFINDER PERF MONITOR", style="bold cyan")
        header_text.append(f"   {now}", style="dim")
        header_text.append(f"   Refresh: {self.refresh_interval}s", style="dim")
        header_text.append("   [q]uit [l]ogs [r]efresh", style="dim yellow")
        return Panel(header_text, box=box.ROUNDED, style="cyan")

    def create_containers_table(self, containers: list[dict]) -> Panel:
        """Create containers status table."""
        table = Table(
            box=box.SIMPLE, expand=True, show_header=True, header_style="bold"
        )
        table.add_column("Container", style="white", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Uptime", justify="right")
        table.add_column("CPU", justify="right")
        table.add_column("Memory", justify="right")
        table.add_column("Net I/O", justify="right")

        for c in containers:
            status_style = "green" if c["status"] == "running" else "red"
            status_icon = "●" if c["status"] == "running" else "○"

            mem_str = ""
            if c["memory_limit"] > 0:
                mem_str = f"{format_bytes(c['memory_usage'])}/{format_bytes(c['memory_limit'])}"

            net_str = f"↓{format_bytes(c['net_rx'])} ↑{format_bytes(c['net_tx'])}"

            table.add_row(
                c["name"],
                Text(f"{status_icon} {c['status']}", style=status_style),
                format_uptime(c["uptime_seconds"]) if c["uptime_seconds"] > 0 else "-",
                f"{c['cpu_percent']:.1f}%",
                mem_str or "-",
                net_str,
            )

        if not containers:
            table.add_row("[dim]No containers found[/dim]", "", "", "", "", "")

        return Panel(
            table, title="[bold]CONTAINERS[/bold]", box=box.ROUNDED, border_style="blue"
        )

    def create_startup_panel(self, metrics: Optional[dict]) -> Panel:
        """Create startup/backend info panel."""
        if not metrics:
            return Panel(
                Text("Backend unavailable", style="red"),
                title="[bold]BACKEND[/bold]",
                box=box.ROUNDED,
                border_style="red",
            )

        startup = metrics.get("startup", {})
        startup_time = startup.get("time_ms", 0)
        uptime = startup.get("uptime_seconds", 0)
        db_ok = startup.get("db_connected", False)
        redis_ok = startup.get("redis_connected", False)

        text = Text()
        text.append(f"Startup: {startup_time:.0f}ms", style="cyan")
        text.append("  │  ", style="dim")
        text.append(f"Uptime: {format_uptime(uptime)}", style="white")
        text.append("  │  ", style="dim")
        text.append(f"DB: ", style="dim")
        text.append("●" if db_ok else "○", style="green" if db_ok else "red")
        text.append("  Redis: ", style="dim")
        text.append("●" if redis_ok else "○", style="green" if redis_ok else "red")

        return Panel(
            text, title="[bold]BACKEND[/bold]", box=box.ROUNDED, border_style="green"
        )

    def create_graph_panel(self, metrics: Optional[dict]) -> Panel:
        """Create graph loading metrics panel."""
        if not metrics:
            return Panel(
                "[dim]No data[/dim]",
                title="[bold]GRAPH LOADING[/bold]",
                box=box.ROUNDED,
            )

        graph = metrics.get("graph", {})

        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="white")

        table.add_row("Total Loads", str(graph.get("loads_total", 0)))
        table.add_row("Cache Hits", str(graph.get("cache_hits", 0)))
        table.add_row("Cache Misses", str(graph.get("cache_misses", 0)))

        hit_rate = graph.get("cache_hit_rate_pct", 0)
        hit_style = "green" if hit_rate >= 80 else "yellow" if hit_rate >= 50 else "red"
        table.add_row("Hit Rate", Text(f"{hit_rate:.1f}%", style=hit_style))

        table.add_row("Avg Time", f"{graph.get('avg_ms', 0):.1f}ms")
        table.add_row("P95 Time", f"{graph.get('p95_ms', 0):.1f}ms")
        table.add_row("Last Time", f"{graph.get('last_ms', 0):.1f}ms")

        return Panel(
            table,
            title="[bold]GRAPH LOADING[/bold]",
            box=box.ROUNDED,
            border_style="magenta",
        )

    def create_algorithms_panel(self, metrics: Optional[dict]) -> Panel:
        """Create algorithm performance panel."""
        if not metrics:
            return Panel(
                "[dim]No data[/dim]", title="[bold]ALGORITHMS[/bold]", box=box.ROUNDED
            )

        algorithms = metrics.get("algorithms", {})

        if not algorithms:
            return Panel(
                "[dim]No algorithm runs yet[/dim]",
                title="[bold]ALGORITHMS[/bold]",
                box=box.ROUNDED,
            )

        table = Table(
            box=box.SIMPLE, expand=True, show_header=True, header_style="bold"
        )
        table.add_column("Algorithm", style="white")
        table.add_column("Runs", justify="right")
        table.add_column("Avg", justify="right")
        table.add_column("P95", justify="right")
        table.add_column("Last", justify="right")
        table.add_column("Trend", justify="left")

        # Sort by number of runs
        sorted_algos = sorted(
            algorithms.items(), key=lambda x: x[1].get("runs", 0), reverse=True
        )

        max_avg = max((a.get("avg_ms", 0) for _, a in sorted_algos), default=1) or 1

        for algo_name, stats in sorted_algos:
            runs = stats.get("runs", 0)
            avg_ms = stats.get("avg_ms", 0)
            p95_ms = stats.get("p95_ms", 0)
            last_ms = stats.get("last_ms", 0)

            # Create a simple bar chart for trend
            bar_width = int((avg_ms / max_avg) * 10)
            bar = "━" * bar_width + "╸" if bar_width < 10 else "━" * 10

            table.add_row(
                algo_name.upper(),
                str(runs),
                f"{avg_ms:.1f}ms",
                f"{p95_ms:.1f}ms",
                f"{last_ms:.1f}ms",
                Text(bar, style="cyan"),
            )

        return Panel(
            table,
            title="[bold]ALGORITHMS[/bold]",
            box=box.ROUNDED,
            border_style="yellow",
        )

    def create_sse_panel(self, metrics: Optional[dict]) -> Panel:
        """Create SSE connections panel."""
        if not metrics:
            return Panel(
                "[dim]No data[/dim]", title="[bold]SSE[/bold]", box=box.ROUNDED
            )

        sse = metrics.get("sse", {})

        text = Text()
        text.append(f"Total: {sse.get('connections_total', 0)}", style="white")
        text.append("  │  ", style="dim")

        active = sse.get("active_connections", 0)
        active_style = "green" if active > 0 else "dim"
        text.append(f"Active: ", style="dim")
        text.append(str(active), style=active_style)

        text.append("  │  ", style="dim")
        text.append(f"Avg: {sse.get('avg_ms', 0):.1f}ms", style="cyan")
        text.append("  │  ", style="dim")
        text.append(f"P95: {sse.get('p95_ms', 0):.1f}ms", style="cyan")

        return Panel(
            text,
            title="[bold]SSE CONNECTIONS[/bold]",
            box=box.ROUNDED,
            border_style="cyan",
        )

    def create_health_panel(
        self, health_ok: bool, health_latency: float, metrics_error: Optional[str]
    ) -> Panel:
        """Create health check panel."""
        text = Text()

        # Health endpoint
        if health_ok:
            text.append("● /health ", style="green")
            text.append(f"{health_latency:.0f}ms", style="dim")
        else:
            text.append("○ /health ", style="red")
            text.append("down", style="dim red")

        text.append("   ", style="dim")

        # Metrics endpoint
        if metrics_error:
            text.append("○ /metrics ", style="red")
            text.append(metrics_error, style="dim red")
        else:
            text.append("● /metrics ", style="green")
            text.append("ok", style="dim")

        return Panel(
            text, title="[bold]HEALTH[/bold]", box=box.ROUNDED, border_style="white"
        )

    def create_logs_panel(self, logs: list[str]) -> Panel:
        """Create logs panel."""
        if not logs:
            return Panel(
                "[dim]No logs available[/dim]",
                title="[bold]LOGS (closest_path_api)[/bold]",
                box=box.ROUNDED,
            )

        # Take last N lines and format
        text = Text()
        for line in logs[-12:]:
            # Truncate very long lines
            if len(line) > 120:
                line = line[:117] + "..."

            # Color based on log level
            if "ERROR" in line or "error" in line:
                text.append(line + "\n", style="red")
            elif "WARNING" in line or "warning" in line:
                text.append(line + "\n", style="yellow")
            elif "INFO" in line:
                text.append(line + "\n", style="dim")
            else:
                text.append(line + "\n", style="dim white")

        return Panel(
            text,
            title="[bold]LOGS (closest_path_api)[/bold]",
            box=box.ROUNDED,
            border_style="dim",
        )

    async def generate_layout(self) -> Layout:
        """Generate the full dashboard layout."""
        # Fetch data
        containers = self.docker_monitor.get_containers()
        metrics = await self.metrics_client.fetch_metrics()
        health_ok, health_latency = await self.metrics_client.health_check()

        # Create layout
        layout = Layout()

        if self.show_logs:
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main", ratio=2),
                Layout(name="logs", ratio=1),
            )
        else:
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main"),
            )

        # Header
        layout["header"].update(self.create_header())

        # Main content
        main_layout = Layout()
        main_layout.split_column(
            Layout(name="top", size=9),
            Layout(name="middle", size=5),
            Layout(name="bottom"),
        )

        # Top row: containers
        main_layout["top"].update(self.create_containers_table(containers))

        # Middle row: startup + graph + sse
        middle_layout = Layout()
        middle_layout.split_row(
            Layout(name="startup", ratio=1),
            Layout(name="graph", ratio=1),
            Layout(name="sse", ratio=1),
        )
        middle_layout["startup"].update(self.create_startup_panel(metrics))
        middle_layout["graph"].update(self.create_graph_panel(metrics))
        middle_layout["sse"].update(self.create_sse_panel(metrics))
        main_layout["middle"].update(middle_layout)

        # Bottom row: algorithms + health
        bottom_layout = Layout()
        bottom_layout.split_column(
            Layout(name="algorithms"),
            Layout(name="health", size=3),
        )
        bottom_layout["algorithms"].update(self.create_algorithms_panel(metrics))
        bottom_layout["health"].update(
            self.create_health_panel(
                health_ok, health_latency, self.metrics_client.last_error
            )
        )
        main_layout["bottom"].update(bottom_layout)

        layout["main"].update(main_layout)

        # Logs panel (if enabled)
        if self.show_logs:
            logs = self.docker_monitor.get_logs("closest_path_api", tail=15)
            layout["logs"].update(self.create_logs_panel(logs))

        return layout

    async def run(self):
        """Run the live dashboard."""
        try:
            with Live(console=console, refresh_per_second=2, screen=True) as live:
                while self.running:
                    layout = await self.generate_layout()
                    live.update(layout)
                    await asyncio.sleep(self.refresh_interval)
        finally:
            await self.metrics_client.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Pathfinder Performance Monitor - Live CLI Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python perf-monitor.py                    # Default 1s refresh
    python perf-monitor.py --refresh 0.5      # Faster refresh
    python perf-monitor.py --logs             # Show log panel
    python perf-monitor.py --api-url http://host:8000
        """,
    )
    parser.add_argument(
        "--refresh",
        "-r",
        type=float,
        default=1.0,
        help="Refresh interval in seconds (default: 1)",
    )
    parser.add_argument("--logs", "-l", action="store_true", help="Show log tail panel")
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    console.print("[bold cyan]Starting Pathfinder Performance Monitor...[/bold cyan]")
    console.print(f"API URL: {args.api_url}")
    console.print(f"Refresh: {args.refresh}s")
    console.print("Press Ctrl+C to exit\n")

    await asyncio.sleep(1)  # Brief pause before going fullscreen

    dashboard = Dashboard(
        refresh_interval=args.refresh,
        show_logs=args.logs,
        api_url=args.api_url,
    )

    try:
        await dashboard.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
