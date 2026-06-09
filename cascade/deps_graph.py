"""Dependency graph analyzer — visualize imports between Python modules."""

import ast
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success


def extract_imports(filepath: Path) -> list[dict[str, Any]]:
    """Extract all imports from a Python file."""
    imports = []
    try:
        tree = ast.parse(filepath.read_text())
    except (SyntaxError, OSError):
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"type": "import", "module": alias.name, "name": alias.asname or alias.name})
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.name
                imports.append({"type": "from", "module": module, "name": name, "alias": alias.asname})

    return imports


def build_graph(root: Path, max_depth: int = 3) -> dict[str, Any]:
    """Build dependency graph for Python project."""
    nodes = set()
    edges = []
    module_map = {}  # filepath -> module name

    # First pass: collect all modules
    for filepath in root.rglob("*.py"):
        if "__pycache__" in str(filepath) or ".git" in str(filepath):
            continue
        rel = filepath.relative_to(root)
        module_name = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
        module_map[str(filepath)] = module_name
        nodes.add(module_name)

    # Second pass: extract edges
    for filepath, module_name in module_map.items():
        imports = extract_imports(Path(filepath))
        for imp in imports:
            target = imp["module"]
            # Check if target is internal
            for other_path, other_module in module_map.items():
                if other_module.startswith(target) or target.startswith(other_module.split(".")[0]):
                    if other_module != module_name:
                        edges.append({"from": module_name, "to": other_module, "type": imp["type"]})
                        nodes.add(other_module)
                    break

    # Calculate metrics
    in_degree = {}
    out_degree = {}
    for n in nodes:
        in_degree[n] = sum(1 for e in edges if e["to"] == n)
        out_degree[n] = sum(1 for e in edges if e["from"] == n)

    # Find cycles (simple check)
    cycles = []
    for e in edges:
        for e2 in edges:
            if e["from"] == e2["to"] and e["to"] == e2["from"]:
                pair = tuple(sorted([e["from"], e["to"]]))
                if pair not in cycles:
                    cycles.append(pair)

    return {
        "nodes": sorted(nodes),
        "edges": edges,
        "metrics": {
            "total_modules": len(nodes),
            "total_imports": len(edges),
            "avg_dependencies": len(edges) / max(len(nodes), 1),
        },
        "in_degree": in_degree,
        "out_degree": out_degree,
        "cycles": cycles,
    }


def format_graph(graph: dict[str, Any], root: Path) -> str:
    """Format dependency graph for terminal display."""
    lines = []
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")
    lines.append(f"{Colors.CYAN}Dependency Graph{Colors.RESET}")
    lines.append(f"{Colors.CYAN}{'─' * 50}{Colors.RESET}")

    m = graph["metrics"]
    lines.append(f"Modules: {m['total_modules']}  Imports: {m['total_imports']}  Avg deps: {m['avg_dependencies']:.1f}")
    lines.append("")

    # Most connected modules
    sorted_by_degree = sorted(
        graph["in_degree"].items(),
        key=lambda x: x[1] + graph["out_degree"].get(x[0], 0),
        reverse=True
    )

    lines.append(f"{Colors.YELLOW}Top connected modules:{Colors.RESET}")
    for mod, indeg in sorted_by_degree[:10]:
        outdeg = graph["out_degree"].get(mod, 0)
        lines.append(f"  {mod}  {Colors.DIM}(in: {indeg}, out: {outdeg}){Colors.RESET}")

    if graph["cycles"]:
        lines.append("")
        lines.append(f"{Colors.RED}⚠ Circular dependencies detected:{Colors.RESET}")
        for a, b in graph["cycles"][:5]:
            lines.append(f"  {a} ↔ {b}")

    # Show some edges
    lines.append("")
    lines.append(f"{Colors.YELLOW}Sample imports:{Colors.RESET}")
    for edge in graph["edges"][:15]:
        lines.append(f"  {edge['from']} → {edge['to']}")
    if len(graph["edges"]) > 15:
        lines.append(f"  {Colors.DIM}... and {len(graph['edges']) - 15} more{Colors.RESET}")

    return "\n".join(lines)


def find_unused_modules(graph: dict[str, Any]) -> list[str]:
    """Find modules with no incoming imports (possibly unused entry points)."""
    unused = []
    for node, indeg in graph["in_degree"].items():
        if indeg == 0:
            unused.append(node)
    return unused
