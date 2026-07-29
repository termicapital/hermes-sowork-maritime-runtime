#!/usr/bin/env python3
"""Dynamic-catalog OpenRouter child tools with parent-enforced human selection."""

from __future__ import annotations

from tools.registry import registry
from safe_proxy_client import MAX_RESULT_CHARS, proxy


def openrouter_catalog(
    query: str = "", output_modality: str = "", limit: int = 50
) -> str:
    """List the bounded live catalog; does not require a selected model."""
    if len(query) > 200 or output_modality not in {
        "",
        "text",
        "image",
        "audio",
        "embeddings",
    }:
        raise ValueError("invalid catalog filter")
    if not 1 <= int(limit) <= 100:
        raise ValueError("catalog limit must be 1..100")
    return proxy(
        "/internal/openrouter/catalog",
        {"query": query, "output_modality": output_modality, "limit": int(limit)},
    )


def openrouter_generate(
    kind: str,
    model: str,
    prompt: str,
    max_tokens: int = 1200,
    voice: str = "alloy",
    format: str = "mp3",
) -> str:
    """Generate only when the parent bound this run to the exact model ID."""
    if kind not in {"text", "image", "audio"} or not model or not prompt:
        raise ValueError("kind, exact model, and prompt are required")
    if len(prompt) > 12000 or not 1 <= int(max_tokens) <= 4000:
        raise ValueError("generation bounds exceeded")
    return proxy(
        "/internal/openrouter/generate",
        {
            "kind": kind,
            "model": model,
            "prompt": prompt,
            "max_tokens": int(max_tokens),
            "voice": voice,
            "format": format,
        },
        timeout=300,
    )


CATALOG_SCHEMA = {
    "name": "openrouter_catalog",
    "description": "List the bounded LIVE OpenRouter catalog (IDs, names, modalities, pricing). Before generation: call this, ask the HUMAN to reply with one exact catalog model ID, then STOP. Do not generate in the same turn.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "maxLength": 200},
            "output_modality": {
                "type": "string",
                "enum": ["", "text", "image", "audio", "embeddings"],
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "additionalProperties": False,
    },
}
GENERATE_SCHEMA = {
    "name": "openrouter_generate",
    "description": "Text, dedicated image, or streaming audio generation. HARD GATE: works only after a later triggering HUMAN message contained this exact live catalog model ID. Never infer/substitute a model or use same-turn approval.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["text", "image", "audio"]},
            "model": {"type": "string", "maxLength": 200},
            "prompt": {"type": "string", "maxLength": 12000},
            "max_tokens": {"type": "integer", "minimum": 1, "maximum": 4000},
            "voice": {"type": "string", "maxLength": 40},
            "format": {
                "type": "string",
                "enum": ["mp3", "wav", "ogg", "flac", "opus", "pcm16"],
            },
        },
        "required": ["kind", "model", "prompt"],
        "additionalProperties": False,
    },
}
registry.register(
    name="openrouter_catalog",
    toolset="openrouter_safe",
    schema=CATALOG_SCHEMA,
    handler=lambda args, **_: openrouter_catalog(**args),
    emoji="📚",
    max_result_size_chars=MAX_RESULT_CHARS,
)
registry.register(
    name="openrouter_generate",
    toolset="openrouter_safe",
    schema=GENERATE_SCHEMA,
    handler=lambda args, **_: openrouter_generate(**args),
    emoji="🔀",
    max_result_size_chars=MAX_RESULT_CHARS,
)
