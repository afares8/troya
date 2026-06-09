"""Benchmark suite for Cascade CLI — compare function performance."""

import time
from pathlib import Path
from typing import Any, Callable

from .ui import Colors, print_error, print_info, print_success


def benchmark_func(func: Callable, *args, iterations: int = 1000, warmup: int = 10) -> dict[str, Any]:
    """Benchmark a function."""
    # Warmup
    for _ in range(warmup):
        func(*args)

    # Actual benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    times.sort()
    total = sum(times)

    return {
        "iterations": iterations,
        "total_time": total,
        "mean": total / iterations,
        "median": times[len(times) // 2],
        "min": times[0],
        "max": times[-1],
        "p95": times[int(iterations * 0.95)],
        "p99": times[int(iterations * 0.99)],
        "ops_per_sec": iterations / total,
    }


def compare_benchmarks(results: dict[str, dict[str, Any]]) -> str:
    """Compare multiple benchmark results."""
    lines = []
    lines.append(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
    lines.append(f"{Colors.CYAN}Benchmark Results{Colors.RESET}")
    lines.append(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")

    # Header
    lines.append(f"{'Function':<20} {'Mean':>12} {'Median':>12} {'Ops/sec':>12} {'Min':>12}")
    lines.append(f"{'─' * 60}")

    # Sort by mean time
    sorted_results = sorted(results.items(), key=lambda x: x[1]["mean"])
    fastest_mean = sorted_results[0][1]["mean"] if sorted_results else 1

    for name, result in sorted_results:
        mean = result["mean"] * 1000  # ms
        median = result["median"] * 1000
        ops = result["ops_per_sec"]
        min_time = result["min"] * 1000

        # Highlight fastest
        color = Colors.GREEN if result["mean"] == fastest_mean else ""
        reset = Colors.RESET if color else ""

        lines.append(
            f"{color}{name:<20}{reset} {mean:>11.3f}ms {median:>11.3f}ms {ops:>11.1f} {min_time:>11.3f}ms"
        )

    # Show improvement relative to fastest
    if len(sorted_results) > 1:
        lines.append("")
        lines.append(f"{Colors.YELLOW}Relative to fastest:{Colors.RESET}")
        fastest = sorted_results[0][1]["mean"]
        for name, result in sorted_results[1:]:
            ratio = result["mean"] / fastest
            lines.append(f"  {name}: {ratio:.2f}x slower")

    return "\n".join(lines)


def run_benchmark_from_string(code: str, func_name: str, iterations: int = 1000) -> dict[str, Any] | None:
    """Benchmark a function defined in a string."""
    namespace = {}
    try:
        exec(code, namespace)
        func = namespace.get(func_name)
        if not func or not callable(func):
            print_error(f"Function '{func_name}' not found in code")
            return None
        return benchmark_func(func, iterations=iterations)
    except Exception as e:
        print_error(f"Error running benchmark: {e}")
        return None


def format_single(result: dict[str, Any], name: str = "Function") -> str:
    """Format a single benchmark result."""
    lines = []
    lines.append(f"{Colors.CYAN}{name}{Colors.RESET}")
    lines.append(f"  Iterations: {result['iterations']:,}")
    lines.append(f"  Mean:       {result['mean'] * 1000:.3f} ms")
    lines.append(f"  Median:     {result['median'] * 1000:.3f} ms")
    lines.append(f"  Min:        {result['min'] * 1000:.3f} ms")
    lines.append(f"  Max:        {result['max'] * 1000:.3f} ms")
    lines.append(f"  P95:        {result['p95'] * 1000:.3f} ms")
    lines.append(f"  P99:        {result['p99'] * 1000:.3f} ms")
    lines.append(f"  Ops/sec:    {result['ops_per_sec']:,.1f}")
    return "\n".join(lines)
