"""LLM client with function calling for multi-agent system."""

import json
import os
from typing import Any

import httpx

DEFAULT_CONFIG = {
    "provider": os.getenv("CASCADE_PROVIDER", "openai"),
    "model": os.getenv("CASCADE_MODEL", "gpt-4o-mini"),
    "api_key": os.getenv("CASCADE_API_KEY", ""),
    "api_base": os.getenv("CASCADE_API_BASE", ""),
    "temperature": 0.5,
    "max_tokens": 2048,
}

URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
}


class LLMClient:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self.provider = self.cfg["provider"]
        self.api_key = self.cfg["api_key"]
        self.model = self.cfg["model"]
        self.api_base = self.cfg["api_base"]
        self.temperature = self.cfg["temperature"]
        self.max_tokens = self.cfg["max_tokens"]

    def chat(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> dict[str, Any]:
        if self.provider == "anthropic":
            return self._chat_anthropic(messages, tools)
        return self._chat_openai(messages, tools)

    def _chat_openai(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> dict[str, Any]:
        url = self.api_base or URLS.get(self.provider, "https://api.openai.com/v1/chat/completions")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]
            result: dict[str, Any] = {"content": msg.get("content", "")}
            if "tool_calls" in msg:
                result["tool_calls"] = [
                    {
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"]),
                    }
                    for tc in msg["tool_calls"]
                ]
            return result
        except Exception as e:
            return {"error": str(e), "content": f"LLM error: {e}"}

    def _chat_anthropic(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        msgs = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": msgs,
            "system": system_msg,
        }
        if tools:
            payload["tools"] = [{"name": t["function"]["name"], "description": t["function"]["description"], "input_schema": t["function"]["parameters"]} for t in tools]

        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", [])
            text = ""
            tool_calls = []
            for block in content:
                if block["type"] == "text":
                    text += block["text"]
                elif block["type"] == "tool_use":
                    tool_calls.append({"name": block["name"], "arguments": block["input"]})
            return {"content": text, "tool_calls": tool_calls}
        except Exception as e:
            return {"error": str(e), "content": f"LLM error: {e}"}
