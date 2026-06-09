"""Advanced edit parser — extract code changes from LLM responses."""

import re
from pathlib import Path
from typing import Any


class EditParser:
    """Parse multiple edit formats from LLM responses."""

    @staticmethod
    def parse(response: str) -> list[dict[str, Any]]:
        """Parse all edits from a response."""
        edits = []

        # Try different formats
        edits.extend(EditParser._parse_diff_blocks(response))
        edits.extend(EditParser._parse_file_blocks(response))
        edits.extend(EditParser._parse_at_syntax(response))
        edits.extend(EditParser._parse_search_replace(response))

        return edits

    @staticmethod
    def _parse_diff_blocks(text: str) -> list[dict[str, Any]]:
        """Parse unified diff blocks."""
        edits = []
        diff_pattern = r'```diff\n(.*?)```'
        for match in re.finditer(diff_pattern, text, re.DOTALL):
            diff_content = match.group(1)
            # Extract filename from ---/+++ lines
            file_match = re.search(r'^---\s+(.+?)\n\+\+\+\s+(.+?)\n', diff_content, re.MULTILINE)
            if file_match:
                filepath = file_match.group(2).strip()
                edits.append({
                    "type": "diff",
                    "file": filepath,
                    "content": diff_content,
                })
        return edits

    @staticmethod
    def _parse_file_blocks(text: str) -> list[dict[str, Any]]:
        """Parse ```python @file.py blocks."""
        edits = []
        # Match code blocks with filename in language specifier
        pattern = r'```(?:\w+)?\s*@?\s*([^\n`]+?)\n(.*?)```'
        for match in re.finditer(pattern, text, re.DOTALL):
            filepath = match.group(1).strip().strip('`').strip()
            content = match.group(2)
            # Validate filepath
            if '/' in filepath or '\\' in filepath or '.' in filepath:
                if not filepath.startswith('http'):
                    edits.append({
                        "type": "create",
                        "file": filepath,
                        "content": content,
                    })
        return edits

    @staticmethod
    def _parse_at_syntax(text: str) -> list[dict[str, Any]]:
        """Parse @filepath
content
 syntax."""
        edits = []
        pattern = r'^@([\w/\\.\-]+)\s*$\n(.*?)(?=\n@|\Z)'
        for match in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            if content:
                edits.append({
                    "type": "create",
                    "file": filepath,
                    "content": content,
                })
        return edits

    @staticmethod
    def _parse_search_replace(text: str) -> list[dict[str, Any]]:
        """Parse SEARCH/REPLACE blocks."""
        edits = []
        pattern = r'(?:SEARCH|FIND):\s*(.*?)\n(.*?)(?:\nREPLACE|WITH):\s*(.*?)\n(.*?)(?=\n(?:SEARCH|FIND):|\Z)'
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            old_text = match.group(2).strip()
            new_text = match.group(4).strip()
            if old_text:
                edits.append({
                    "type": "replace",
                    "old": old_text,
                    "new": new_text,
                })
        return edits

    @staticmethod
    def apply_edits(edits: list[dict[str, Any]], cwd: Path) -> dict[str, Any]:
        """Apply parsed edits to files."""
        applied = 0
        failed = 0
        errors = []

        for edit in edits:
            try:
                if edit["type"] == "create":
                    filepath = cwd / edit["file"]
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    filepath.write_text(edit["content"])
                    applied += 1

                elif edit["type"] == "diff":
                    # Apply unified diff (simplified)
                    applied += EditParser._apply_diff(edit["content"], cwd)

                elif edit["type"] == "replace":
                    # Try to find and replace in recently modified files
                    for pyfile in cwd.rglob("*.py"):
                        content = pyfile.read_text()
                        if edit["old"] in content:
                            new_content = content.replace(edit["old"], edit["new"])
                            pyfile.write_text(new_content)
                            applied += 1
                            break

            except Exception as e:
                failed += 1
                errors.append(str(e))

        return {
            "applied": applied,
            "failed": failed,
            "errors": errors,
        }

    @staticmethod
    def _apply_diff(diff_content: str, cwd: Path) -> int:
        """Apply a unified diff. Returns number of files modified."""
        count = 0
        current_file = None
        current_content = None

        for line in diff_content.split("\n"):
            if line.startswith("+++"):
                current_file = line[4:].strip().split("\t")[0]
                if current_file.startswith("b/"):
                    current_file = current_file[2:]
                current_content = []
            elif line.startswith("+") and not line.startswith("+++"):
                if current_content is not None:
                    current_content.append(line[1:])

        if current_file and current_content:
            filepath = cwd / current_file
            if filepath.exists():
                filepath.write_text("\n".join(current_content))
                count += 1

        return count


def extract_code_blocks(text: str) -> list[dict[str, str]]:
    """Extract all code blocks from text."""
    blocks = []
    pattern = r'```(\w+)?\n(.*?)```'
    for match in re.finditer(pattern, text, re.DOTALL):
        blocks.append({
            "language": match.group(1) or "text",
            "code": match.group(2),
        })
    return blocks
