"""Multi-agent orchestrator with task delegation and tool execution."""

import asyncio
import json
from typing import Any

from .db import (
    create_task,
    get_messages,
    list_agents,
    log_message,
    log_tool_call,
    register_agent,
    update_agent,
    update_task,
)
from .llm import LLMClient
from .tools import ToolRegistry

AGENT_PROMPTS = {
    "coder": (
        "You are an expert software engineer. You write clean, efficient code. "
        "You can read files, write files, run Python code, and search for patterns. "
        "When given a task, think step by step and use tools to accomplish it."
    ),
    "researcher": (
        "You are a research analyst. You gather information by reading files, "
        "searching text, and analyzing code. You provide detailed summaries."
    ),
    "reviewer": (
        "You are a senior code reviewer. You analyze code for bugs, "
        "security issues, and best practices. You suggest improvements."
    ),
    "tester": (
        "You are a QA engineer. You write tests, run code, and verify "
        "that implementations meet requirements. You report on coverage."
    ),
}


class Agent:
    def __init__(self, name: str, role: str, model: str, client: LLMClient) -> None:
        self.name = name
        self.role = role
        self.client = client
        self.tools = ToolRegistry()
        self.system_prompt = AGENT_PROMPTS.get(role, "You are a helpful assistant.")
        register_agent(name, role, model)

    async def run(self, task_id: int, instruction: str, context: str = "") -> str:
        update_agent(self.name, status="working")
        log_message(task_id, self.name, "user", f"Task: {instruction}\n\nContext: {context}")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Task: {instruction}\n\nContext:\n{context}"},
        ]

        max_steps = 5
        for step in range(max_steps):
            # Get previous messages for this task
            prev = get_messages(task_id)
            for m in prev:
                if m["agent_name"] == self.name and m["role"] in ("assistant", "tool"):
                    messages.append({"role": m["role"], "content": m["content"]})

            tool_defs = self.tools.get_definitions()
            result = self.client.chat(messages, tools=tool_defs)

            if "error" in result:
                log_message(task_id, self.name, "assistant", f"Error: {result['error']}")
                update_agent(self.name, status="idle")
                return f"Error: {result['error']}"

            content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])

            log_message(task_id, self.name, "assistant", content, tool_calls=tool_calls)

            if not tool_calls:
                update_agent(self.name, status="idle")
                return content

            # Execute tools and continue
            for tc in tool_calls:
                tool_result = self.tools.execute(tc["name"], tc["arguments"])
                log_tool_call(task_id, self.name, tc["name"], tc["arguments"], tool_result)
                tool_msg = f"Tool '{tc['name']}' result: {json.dumps(tool_result, default=str)[:500]}"
                log_message(task_id, self.name, "tool", tool_msg)
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "tool", "content": json.dumps(tool_result, default=str)})

        update_agent(self.name, status="idle")
        return content + "\n(Reached max tool steps)"


class Orchestrator:
    def __init__(self, llm_config: dict[str, Any] | None = None) -> None:
        self.client = LLMClient(llm_config)
        self.agents: dict[str, Agent] = {}
        self.running = False

    def create_agent(self, name: str, role: str, model: str | None = None) -> Agent:
        model = model or self.client.model
        agent = Agent(name, role, model, self.client)
        self.agents[name] = agent
        return agent

    async def delegate(self, task_title: str, task_description: str) -> dict[str, Any]:
        task_id = create_task(task_title, task_description)

        # Determine which agents to use
        agents = list(self.agents.values())
        if not agents:
            update_task(task_id, status="failed", result="No agents available")
            return {"task_id": task_id, "status": "failed", "result": "No agents"}

        # Simple delegation: use first agent that matches, or default to first
        agent = agents[0]
        for a in agents:
            if a.role in task_description.lower() or a.role in task_title.lower():
                agent = a
                break

        update_task(task_id, status="in_progress", assigned_to=agent.name)
        result = await agent.run(task_id, task_description)
        update_task(task_id, status="completed", result=result)
        return {"task_id": task_id, "status": "completed", "result": result, "agent": agent.name}

    async def run_pipeline(self, title: str, steps: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Run a multi-step pipeline across agents."""
        results = []
        context = ""
        for step in steps:
            role = step.get("agent", "coder")
            instruction = step["instruction"]
            agent = next((a for a in self.agents.values() if a.role == role), list(self.agents.values())[0])
            task_id = create_task(f"{title} - {role}", instruction)
            update_task(task_id, status="in_progress", assigned_to=agent.name)
            result = await agent.run(task_id, instruction, context)
            update_task(task_id, status="completed", result=result)
            results.append({"task_id": task_id, "agent": agent.name, "result": result})
            context += f"\n\n{agent.name} ({agent.role}) result:\n{result}"
        return results
