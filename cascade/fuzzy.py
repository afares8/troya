"""Fuzzy file finder for Cascade CLI — fzf-like experience."""

import os
from pathlib import Path
from typing import Any


def _fuzzy_score(query: str, text: str) -> float:
    """Calculate fuzzy match score. Higher = better match."""
    query = query.lower()
    text = text.lower()

    if query == text:
        return 1000.0  # exact match
    if query in text:
        return 500.0 + (len(text) - len(query)) * -0.1  # substring, prefer shorter

    # Fuzzy character matching
    score = 0.0
    query_idx = 0
    last_match_idx = -1

    for i, char in enumerate(text):
        if query_idx < len(query) and char == query[query_idx]:
            score += 10.0
            if last_match_idx >= 0:
                gap = i - last_match_idx - 1
                score -= gap * 2.0  # penalty for gaps
            if i == 0 or text[i - 1] in "_/\\-. ":
                score += 5.0  # bonus for word boundaries
            last_match_idx = i
            query_idx += 1

    if query_idx < len(query):
        return 0.0  # didn't match all characters

    # Penalty for longer paths
    score -= len(text) * 0.1
    return max(score, 0.1)


def fuzzy_find(query: str, root: Path = Path("."), max_results: int = 20, max_depth: int = 5) -> list[tuple[Path, float]]:
    """Find files matching query with fuzzy scoring."""
    results = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath_path = Path(dirpath)
        depth = len(dirpath_path.relative_to(root).parts)
        if depth > max_depth:
            del dirnames[:]
            continue

        for filename in filenames:
            filepath = dirpath_path / filename
            rel = str(filepath.relative_to(root))

            # Skip hidden and common ignore patterns
            if "/." in rel or "__pycache__" in rel or "node_modules" in rel or ".git" in rel:
                continue

            score = _fuzzy_score(query, rel)
            if score > 0:
                results.append((filepath, score))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:max_results]


def interactive_fuzzy_find(query: str, root: Path = Path(".")) -> Path | None:
    """Find a file and return it."""
    results = fuzzy_find(query, root, max_results=10)
    if not results:
        return None
    # Return best match
    return results[0][0]


def format_results(results: list[tuple[Path, float]], root: Path = Path(".")) -> str:
    """Format fuzzy find results for display."""
    from .ui import Colors

    if not results:
        return f"{Colors.YELLOW}No matches found{Colors.RESET}"

    lines = [f"{Colors.CYAN}Fuzzy matches:{Colors.RESET}"]
    for i, (path, score) in enumerate(results, 1):
        rel = str(path.relative_to(root))
        lines.append(f"  {Colors.YELLOW}{i}.{Colors.RESET} {rel} {Colors.DIM}(score: {score:.1f}){Colors.RESET}")
    return "\n".join(lines)
