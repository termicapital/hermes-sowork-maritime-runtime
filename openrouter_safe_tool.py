#!/usr/bin/env python3
"""Restricted OpenRouter tool: no credential is present in the Hermes child."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from tools.registry import registry

ENDPOINT = "http://127.0.0.1:8765/internal/openrouter/query"
TOKEN_PATH = Path("/opt/data/discovery-runtime/openrouter-proxy-token")


def openrouter_query(model: str, prompt: str, max_tokens: int = 600) -> dict[str, Any]:
    model = str(model).strip()
    prompt = str(prompt).strip()
    max_tokens = int(max_tokens)
    if not model or not prompt:
        raise ValueError("model and prompt are required")
    if len(prompt) > 12000:
        raise ValueError("prompt exceeds 12,000 characters")
    if max_tokens < 1 or max_tokens > 1200:
        raise ValueError("max_tokens must be between 1 and 1200")
    body = json.dumps({"model": model, "prompt": prompt, "max_tokens": max_tokens}).encode("utf-8")
    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise RuntimeError("OpenRouter proxy capability is unavailable")
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Discovery-Internal-Token": token,
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw_response = response.read(25_001)
    if len(raw_response) > 25_000:
        raise RuntimeError("OpenRouter proxy response exceeded 25 KB")
    return json.loads(raw_response.decode("utf-8"))


SCHEMA = {
    "name": "openrouter_query",
    "description": (
        "Run a bounded prompt through one approved OpenRouter model. The API key "
        "stays in the parent service and is never exposed to this agent. Use for "
        "explicit model comparisons or when the requester asks for OpenRouter."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "enum": [
                    "openai/gpt-4o-mini",
                    "google/gemini-2.5-flash",
                    "anthropic/claude-sonnet-4",
                    "openrouter/auto",
                ],
            },
            "prompt": {"type": "string", "maxLength": 12000},
            "max_tokens": {"type": "integer", "minimum": 1, "maximum": 1200, "default": 600},
        },
        "required": ["model", "prompt"],
        "additionalProperties": False,
    },
}

registry.register(
    name="openrouter_query",
    toolset="openrouter_safe",
    schema=SCHEMA,
    handler=lambda args, **_kwargs: openrouter_query(
        args.get("model", ""), args.get("prompt", ""), args.get("max_tokens", 600)
    ),
    emoji="🔀",
    max_result_size_chars=20_000,
)
