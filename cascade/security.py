"""Security scanner for Cascade CLI — detects secrets, API keys, and vulnerabilities."""

import re
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success, print_warning


# Secret patterns
SECRET_PATTERNS = {
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Key": r"['\"\s][A-Za-z0-9/+=]{40}['\"\s]",
    "GitHub Token": r"gh[pousr]_[A-Za-z0-9_]{36,}",
    "OpenAI API Key": r"sk-[a-zA-Z0-9]{20,}",
    "Slack Token": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*",
    "Generic API Key": r"(api_key|apikey|api-key)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]",
    "Generic Secret": r"(secret|password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
    "Private Key": r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
    "Database URL": r"(postgres|mysql|mongodb)://[^:]+:[^@]+@[^/]+",
    "JWT Token": r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
}

# Vulnerability patterns
VULN_PATTERNS = {
    "SQL Injection": r"(execute|query|cursor\.execute)\s*\(.*%s.*\)|f[\"'].*SELECT.*\{.*\}.*[\"']",
    "Hardcoded Password": r"password\s*=\s*['\"][^'\"]+['\"]",
    "Eval Usage": r"\beval\s*\(",
    "Exec Usage": r"\bexec\s*\(",
    "Pickle Load": r"pickle\.loads?\s*\(",
    "YAML Load": r"yaml\.load\s*\([^,)]*\)",
    "Shell True": r"shell\s*=\s*True",
    "Debug Mode": r"debug\s*=\s*True",
    "Disabled Verify": r"verify\s*=\s*False",
    "Mako Template": r"MakoTemplate\s*\(|Template\s*\(.*lookup\s*=",
}


def scan_file(filepath: Path) -> list[dict[str, Any]]:
    """Scan a single file for secrets and vulnerabilities."""
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.split("\n")
    except (OSError, UnicodeDecodeError):
        return findings

    for lineno, line in enumerate(lines, 1):
        # Skip comments and docstrings for some checks
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        for name, pattern in SECRET_PATTERNS.items():
            for match in re.finditer(pattern, line, re.IGNORECASE):
                # Skip test files with fake data
                if "test" in str(filepath).lower() and "fake" in line.lower():
                    continue
                if "example" in line.lower() or "placeholder" in line.lower():
                    continue

                findings.append({
                    "type": "secret",
                    "category": name,
                    "line": lineno,
                    "column": match.start(),
                    "match": match.group()[:30] + "..." if len(match.group()) > 30 else match.group(),
                    "severity": "critical" if name in {"AWS Secret Key", "Private Key", "OpenAI API Key"} else "high",
                    "file": str(filepath),
                })

        for name, pattern in VULN_PATTERNS.items():
            for match in re.finditer(pattern, line, re.IGNORECASE):
                findings.append({
                    "type": "vulnerability",
                    "category": name,
                    "line": lineno,
                    "column": match.start(),
                    "match": match.group()[:50],
                    "severity": "high" if name in {"SQL Injection", "Eval Usage", "Exec Usage"} else "medium",
                    "file": str(filepath),
                })

    return findings


def scan_project(root: Path, max_files: int = 200) -> dict[str, Any]:
    """Scan entire project for security issues."""
    all_findings = []
    scanned = 0

    for filepath in root.rglob("*"):
        if scanned >= max_files:
            break
        if not filepath.is_file():
            continue
        if filepath.stat().st_size > 100_000:
            continue
        if filepath.suffix not in {".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env", ".cfg", ".ini", ".go", ".rs", ".java", ".cpp", ".rb", ".php"}:
            continue
        if "node_modules" in str(filepath) or "__pycache__" in str(filepath) or ".git" in str(filepath):
            continue

        findings = scan_file(filepath)
        all_findings.extend(findings)
        scanned += 1

    critical = [f for f in all_findings if f["severity"] == "critical"]
    high = [f for f in all_findings if f["severity"] == "high"]
    medium = [f for f in all_findings if f["severity"] == "medium"]

    return {
        "total": len(all_findings),
        "critical": len(critical),
        "high": len(high),
        "medium": len(medium),
        "findings": all_findings,
        "scanned": scanned,
    }


def format_report(report: dict[str, Any]) -> str:
    """Format security scan results."""
    lines = []
    lines.append(f"{Colors.RED}{'─' * 50}{Colors.RESET}")
    lines.append(f"{Colors.RED}Security Scan Report{Colors.RESET}")
    lines.append(f"{Colors.RED}{'─' * 50}{Colors.RESET}")
    lines.append(f"Files scanned: {report['scanned']}")
    lines.append(f"Findings: {report['critical']} critical, {report['high']} high, {report['medium']} medium")
    lines.append("")

    if not report["findings"]:
        lines.append(f"{Colors.GREEN}✓ No security issues found{Colors.RESET}")
        return "\n".join(lines)

    # Group by severity
    for severity in ["critical", "high", "medium"]:
        findings = [f for f in report["findings"] if f["severity"] == severity]
        if not findings:
            continue

        color = {"critical": Colors.RED, "high": Colors.YELLOW, "medium": Colors.CYAN}[severity]
        lines.append(f"{color}{severity.upper()} ({len(findings)}){Colors.RESET}")

        for f in findings[:10]:
            rel_file = f["file"]
            lines.append(f"  {Colors.YELLOW}{rel_file}:{f['line']}{Colors.RESET}")
            lines.append(f"    {color}[{f['category']}]{Colors.RESET} {f['match']}")

        if len(findings) > 10:
            lines.append(f"  {Colors.DIM}... and {len(findings) - 10} more{Colors.RESET}")
        lines.append("")

    return "\n".join(lines)
