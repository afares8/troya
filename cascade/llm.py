"""LLM client supporting multiple providers."""

import json
import os
from typing import Any

import httpx

from .ui import Colors, print_error, stream_chunk


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token for English/code."""
    return max(1, len(text) // 4)


def estimate_cost(tokens: int, model: str) -> float:
    """Very rough cost estimation in USD (per 1M tokens)."""
    costs = {
        "gpt-4o": 0.005,
        "gpt-4o-mini": 0.0006,
        "gpt-4": 0.03,
        "claude-3-5-sonnet": 0.003,
        "claude-3-5-sonnet-20241022": 0.003,
        "llama-3.1-70b": 0.00059,
        "llama-3.1-8b": 0.00005,
    }
    # Match partial model names
    for key, rate in costs.items():
        if key in model.lower():
            return (tokens / 1_000_000) * rate
    return 0.0


class LLMClient:
    """Generic LLM client for OpenAI, Anthropic, Ollama, and custom endpoints."""

    PROVIDERS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "header": "Authorization",
            "prefix": "Bearer ",
            "chat_endpoint": "/chat/completions",
            "body_key": "messages",
            "stream_format": "openai",
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "header": "x-api-key",
            "prefix": "",
            "chat_endpoint": "/messages",
            "body_key": "messages",
            "stream_format": "anthropic",
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "header": "Authorization",
            "prefix": "Bearer ",
            "chat_endpoint": "/chat/completions",
            "body_key": "messages",
            "stream_format": "openai",
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "header": "Authorization",
            "prefix": "Bearer ",
            "chat_endpoint": "/chat/completions",
            "body_key": "messages",
            "stream_format": "openai",
        },
        "custom": {
            "base_url": "",
            "header": "Authorization",
            "prefix": "Bearer ",
            "chat_endpoint": "/chat/completions",
            "body_key": "messages",
            "stream_format": "openai",
        },
    }

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.provider = config.get("provider", "openai").lower()
        self.model = config.get("model", "gpt-4o")
        self.api_key = config.get("api_key", "")
        self.api_base = config.get("api_base", "")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)
        self.streaming = config.get("streaming", True)

        if self.provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {self.provider}")

        self.provider_cfg = self.PROVIDERS[self.provider]

        if self.api_base:
            self.base_url = self.api_base.rstrip("/")
        else:
            self.base_url = self.provider_cfg["base_url"]

        self.client = httpx.Client(timeout=120.0, follow_redirects=True)

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.provider == "anthropic":
            headers["anthropic-version"] = "2023-06-01"
            headers[self.provider_cfg["header"]] = self.api_key
        elif self.api_key:
            headers[self.provider_cfg["header"]] = f"{self.provider_cfg['prefix']}{self.api_key}"
        return headers

    def _build_body(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if self.provider == "anthropic":
            # Anthropic expects system as top-level param
            system_msg = ""
            filtered_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    filtered_messages.append(msg)
            return {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_msg,
                "messages": filtered_messages,
                "stream": self.streaming,
            }
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
            "stream": self.streaming,
        }

    def count_tokens(self, messages: list[dict[str, str]]) -> int:
        """Estimate tokens for a message list."""
        total = 0
        for msg in messages:
            total += estimate_tokens(msg.get("content", ""))
            total += estimate_tokens(msg.get("role", ""))
        return total

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send chat request and return full response."""
        input_tokens = self.count_tokens(messages)
        url = f"{self.base_url}{self.provider_cfg['chat_endpoint']}"
        body = self._build_body(messages)
        headers = self._get_headers()

        try:
            if self.streaming:
                return self._stream_chat(url, body, headers)
            else:
                return self._sync_chat(url, body, headers)
        except httpx.ConnectError as e:
            print_error(f"Connection error: {e}. Check your API base URL or network.")
            return ""
        except httpx.HTTPStatusError as e:
            print_error(f"API error: {e.response.status_code} - {e.response.text[:500]}")
            return ""
        except Exception as e:
            print_error(f"Request failed: {e}")
            return ""

    def _sync_chat(self, url: str, body: dict, headers: dict) -> str:
        response = self.client.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()

        if self.provider == "anthropic":
            return data.get("content", [{}])[0].get("text", "")
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _stream_chat(self, url: str, body: dict, headers: dict) -> str:
        body["stream"] = True
        full_response = []

        with self.client.stream("POST", url, json=body, headers=headers) as response:
            response.raise_for_status()
            print(f"{Colors.MAGENTA}{Colors.BOLD}Cascade:{Colors.RESET}\n", end="")

            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8") if isinstance(line, bytes) else line

                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        chunk = self._extract_chunk(data)
                        if chunk:
                            stream_chunk(chunk)
                            full_response.append(chunk)
                    except json.JSONDecodeError:
                        continue
                elif line.startswith("event: "):
                    continue
                elif line.startswith(":"):
                    # SSE comment/keepalive
                    continue

            print()  # final newline

        # Print token/cost estimate
        output = "".join(full_response)
        output_tokens = estimate_tokens(output)
        cost = estimate_cost(output_tokens, self.model)
        if cost > 0:
            print(f"{Colors.DIM}(~{output_tokens} tokens, est. ${cost:.4f}){Colors.RESET}")
        return output

    def _extract_chunk(self, data: dict) -> str:
        """Extract text chunk from streaming response."""
        if self.provider == "anthropic":
            # Anthropic streaming: content_block_delta events
            if "delta" in data:
                return data["delta"].get("text", "")
            return ""

        # OpenAI-compatible format
        choices = data.get("choices", [{}])
        if choices:
            delta = choices[0].get("delta", {})
            return delta.get("content", "")
        return ""

    def close(self) -> None:
        self.client.close()
