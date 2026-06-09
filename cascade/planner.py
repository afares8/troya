"""Task planner for Cascade CLI - decomposes complex requests into multi-step plans."""

import json
import re
from typing import Any

PLANNER_SYSTEM_PROMPT = (
    "You are a planning assistant. Given a user's request, break it down into a clear, "
    "numbered plan of concrete steps. Each step should be specific and actionable. "
    "If the request is simple (one step), just say so. "
    "Respond ONLY with the plan, no extra text."
)


def create_plan(client, request: str) -> list[dict[str, Any]]:
    """Ask the LLM to decompose a request into steps."""
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Create a plan for this task: {request}\n\n"
                'Respond in JSON format: {"steps": [{"step": 1, "description": "...", "estimated_time": "2 min"}]}'
            ),
        },
    ]
    response = client.chat(messages)
    if not response:
        return [{"step": 1, "description": request, "estimated_time": "?"}]

    # Try to extract JSON
    try:
        # Find JSON block
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if "steps" in data and isinstance(data["steps"], list):
                return data["steps"]
    except json.JSONDecodeError:
        pass

    # Fallback: parse numbered list
    steps = []
    for line in response.splitlines():
        m = re.match(r'(?:\d+[.\)]\s*)(.+)', line.strip())
        if m:
            steps.append({"step": len(steps) + 1, "description": m.group(1).strip(), "estimated_time": "?"})

    if not steps:
        return [{"step": 1, "description": request, "estimated_time": "?"}]
    return steps


def format_plan(steps: list[dict[str, Any]]) -> str:
    """Format plan for display."""
    lines = ["📋 Plan:"]
    for s in steps:
        lines.append(f"  {s['step']}. {s['description']} ({s.get('estimated_time', '?')})")
    return "\n".join(lines)
