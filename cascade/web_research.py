"""Web research module for Cascade CLI — search and scrape docs."""

import re
import subprocess
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_warning


def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web using available tools."""
    results = []

    # Try duckduckgo (ddgr)
    try:
        r = subprocess.run(
            ["ddgr", "--json", "--num", str(max_results), "--noprompt", query],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            import json
            for item in json.loads(r.stdout):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "abstract": item.get("abstract", ""),
                })
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    # Fallback: try googler (googler)
    if not results:
        try:
            r = subprocess.run(
                ["googler", "--json", "-n", str(max_results), "--noprompt", query],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0:
                import json
                for item in json.loads(r.stdout):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "abstract": item.get("abstract", ""),
                    })
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

    # Fallback: try surfraw
    if not results:
        try:
            r = subprocess.run(
                ["surfraw", "-browser=/bin/echo", "duckduckgo", query],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n")[:max_results]:
                    if line.startswith("http"):
                        results.append({
                            "title": "Search result",
                            "url": line.strip(),
                            "abstract": "",
                        })
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return results


def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    # Try curl first
    try:
        r = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "10", "-A", "Mozilla/5.0", url],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            return _extract_text(r.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Try wget
    try:
        r = subprocess.run(
            ["wget", "-qO-", "--timeout=10", "--user-agent=Mozilla/5.0", url],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            return _extract_text(r.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return f"Could not fetch {url}. Install curl or wget."


def _extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    # Remove scripts and styles
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Clean up
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", "", text)
    text = re.sub(r"\s+", " ", text)

    # Extract paragraphs
    lines = text.split(". ")
    paragraphs = []
    current = []
    for line in lines:
        current.append(line)
        if len(" ".join(current)) > 200:
            paragraphs.append(". ".join(current) + ".")
            current = []
    if current:
        paragraphs.append(". ".join(current) + ".")

    return "\n\n".join(paragraphs[:20])


def research_topic(query: str) -> str:
    """Research a topic and return summarized findings."""
    print_info(f"Researching: {query}")

    results = search_web(query)
    if not results:
        return f"{Colors.YELLOW}No web search results found. Install ddgr or googler for web search.{Colors.RESET}"

    findings = []
    for result in results[:3]:
        content = fetch_url(result["url"])
        findings.append({
            "title": result["title"],
            "url": result["url"],
            "content": content[:2000],
        })

    # Format findings
    lines = [f"{Colors.CYAN}Research Results: {query}{Colors.RESET}", ""]
    for f in findings:
        lines.append(f"{Colors.YELLOW}{f['title']}{Colors.RESET}")
        lines.append(f"{Colors.DIM}{f['url']}{Colors.RESET}")
        lines.append(f["content"][:500])
        lines.append("")

    return "\n".join(lines)
