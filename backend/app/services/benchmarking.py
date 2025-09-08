"""
Performance benchmarking suite for pathfinding algorithms.

Benchmarks:
- Time complexity (computation time vs graph size)
- Space complexity (memory usage vs graph size)
- Algorithm comparison (same graph, different algorithms)
- Scalability (performance degradation)
"""

import asyncio
import time
import networkx as nx
from typing import Dict, List, Tuple
from dataclasses import dataclass

from app.services.pathfinding import get_pathfinder, PathResult


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""
    algorithm: str
    nodes: int
    edges: int
    computation_time_ms: float
    memory_usage_mb: float
    nodes_explored: int
    path_length: int
    path_cost: float
    success: bool


class GraphGenerator:
    """Generate test graphs of various sizes and topologies."""

    @staticmethod
    def grid_graph(rows: int, cols: int) -> nx.DiGraph:
        """Generate a grid graph (rectangular)."""
        g = nx.DiGraph()
        
        # Create nodes with coordinates
        for i in range(rows):
            for j in range(cols):
                node_id = f"node_{i}_{j}"
                g.add_node(node_id, lat=float(i), lon=float(j))
        
        # Add edges with uniform weights
        for i in range(rows):
            for j in range(cols):
                current = f"node_{i}_{j}"
                
                # Right neighbor
                if j + 1 < cols:
                    neighbor = f"node_{i}_{j + 1}"
                    g.add_edge(current, neighbor, distance=1.0)
                
                # Down neighbor
                if i + 1 < rows:
                    neighbor = f"node_{i + 1}_{j}"
                    g.add_edge(current, neighbor, distance=1.0)
        
        return g

    @staticmethod
    def random_graph(num_nodes: int, edge_probability: float = 0.1) -> nx.DiGraph:
        """Generate a random Erdős-Rényi graph."""
        g = nx.gnp_random_graph(num_nodes, edge_probability, directed=True)
        
        # Add coordinates and weights
        for i, node in enumerate(g.nodes()):
            g.nodes[node]["lat"] = float(i % 100)
            g.nodes[node]["lon"] = float(i // 100)
        
        for u, v in g.edges():
            g[u][v]["distance"] = 1.0 + ((u + v) % 10) * 0.5
        
        return g

    @staticmethod
    def scale_free_graph(num_nodes: int) -> nx.DiGraph:
        """Generate a scale-free graph (power-law degree distribution)."""
        g = nx.scale_free_graph(num_nodes)
        
        # Make it directed
        g = nx.DiGraph(g)
        
        # Add coordinates and weights
        for i, node in enumerate(g.nodes()):
            g.nodes[node]["lat"] = float(i % 100)
            g.nodes[node]["lon"] = float(i // 100)
        
        for u, v in g.edges():
            g[u][v]["distance"] = 1.0 + ((u + v) % 10) * 0.5
        
        return g


class Benchmarker:
    """Run performance benchmarks on pathfinding algorithms."""

    def __init__(self):
        self.gen = GraphGenerator()
        self.results: List[BenchmarkResult] = []

    async def benchmark_algorithm_on_graph(
        self,
        algorithm_name: str,
        graph: nx.DiGraph,
        start_node: str = None,
        end_node: str = None,
        **kwargs
    ) -> BenchmarkResult:
        """Run a single algorithm on a graph."""
        nodes = list(graph.nodes())
        
        # Use provided or select first/last nodes
        if start_node is None:
            start_node = nodes[0]
        if end_node is None:
            end_node = nodes[-1]
        
        # Initialize algorithm
        try:
            pathfinder = get_pathfinder(algorithm_name, **kwargs)
        except ValueError:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")
        
        # Run algorithm
        result: PathResult = await pathfinder.find_path(
            graph, start_node, end_node, "distance", websocket=None
        )
        
        benchmark_result = BenchmarkResult(
            algorithm=algorithm_name,
            nodes=len(graph.nodes()),
            edges=len(graph.edges()),
            computation_time_ms=result.computation_time_ms,
            memory_usage_mb=result.memory_usage_mb,
            nodes_explored=result.nodes_explored,
            path_length=len(result.path),
            path_cost=result.cost,
            success=result.success,
        )
        
        self.results.append(benchmark_result)
        return benchmark_result

    async def compare_algorithms(
        self,
        algorithms: List[str],
        graph: nx.DiGraph,
        start_node: str = None,
        end_node: str = None,
        **kwargs
    ) -> List[BenchmarkResult]:
        """Compare multiple algorithms on the same graph."""
        results = []
        
        for algo in algorithms:
            try:
                result = await self.benchmark_algorithm_on_graph(
                    algo, graph, start_node, end_node, **kwargs
                )
                results.append(result)
            except Exception as e:
                print(f"Error benchmarking {algo}: {e}")
        
        return results

    async def scalability_test(
        self,
        algorithm_name: str,
        graph_sizes: List[int],
        graph_type: str = "grid",
        **kwargs
    ) -> List[BenchmarkResult]:
        """Test algorithm scalability across different graph sizes."""
        results = []
        
        for size in graph_sizes:
            try:
                # Generate graph
                if graph_type == "grid":
                    cols = int(size ** 0.5)
                    rows = (size + cols - 1) // cols
                    graph = self.gen.grid_graph(rows, cols)
                elif graph_type == "random":
                    graph = self.gen.random_graph(size)
                elif graph_type == "scale_free":
                    graph = self.gen.scale_free_graph(size)
                else:
                    raise ValueError(f"Unknown graph type: {graph_type}")
                
                # Benchmark on this size
                result = await self.benchmark_algorithm_on_graph(
                    algorithm_name, graph, **kwargs
                )
                results.append(result)
                
                print(f"  {algorithm_name}: {size} nodes -> "
                      f"{result.computation_time_ms:.2f}ms, "
                      f"{result.memory_usage_mb:.4f}MB")
            
            except Exception as e:
                print(f"Error on size {size}: {e}")
        
        return results

    async def full_benchmark(
        self,
        algorithms: List[str],
        graph_sizes: List[int] = None,
        iterations: int = 3,
    ) -> Dict:
        """Run comprehensive benchmark suite."""
        if graph_sizes is None:
            graph_sizes = [100, 500, 1000]
        
        report = {
            "algorithms": algorithms,
            "graph_sizes": graph_sizes,
            "iterations": iterations,
            "results_by_size": {},
        }
        
        for size in graph_sizes:
            print(f"\n📊 Benchmarking {size}-node graph...")
            
            # Generate graph
            cols = int(size ** 0.5)
            rows = (size + cols - 1) // cols
            graph = self.gen.grid_graph(rows, cols)
            
            # Benchmark each algorithm
            size_results = await self.compare_algorithms(algorithms, graph)
            report["results_by_size"][size] = [
                {
                    "algorithm": r.algorithm,
                    "computation_time_ms": r.computation_time_ms,
                    "memory_usage_mb": r.memory_usage_mb,
                    "nodes_explored": r.nodes_explored,
                    "path_length": r.path_length,
                    "success": r.success,
                }
                for r in size_results
            ]
        
        return report
