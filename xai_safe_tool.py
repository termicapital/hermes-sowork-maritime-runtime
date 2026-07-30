"""Bounded xAI Responses web/X research child tool."""

from tools.registry import registry
from safe_proxy_client import MAX_RESULT_CHARS, proxy


def xai_safe(prompt, model="grok-4.5", tools=None, max_output_tokens=1200):
    return proxy(
        "/internal/xai",
        {
            "prompt": prompt,
            "model": model,
            "tools": tools or ["web_search"],
            "max_output_tokens": max_output_tokens,
        },
    )


SCHEMA = {
    "name": "xai_safe",
    "description": "Call fixed xAI Responses API with grok-4.5 and only web_search/x_search. Code interpreter, file search, and arbitrary tools are impossible.",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "maxLength": 12000},
            "model": {"type": "string", "enum": ["grok-4.5"]},
            "tools": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {"type": "string", "enum": ["web_search", "x_search"]},
            },
            "max_output_tokens": {"type": "integer", "minimum": 1, "maximum": 4000},
        },
        "required": ["prompt"],
        "additionalProperties": False,
    },
}
registry.register(
    name="xai_safe",
    toolset="xai_safe",
    schema=SCHEMA,
    handler=lambda args, **_: xai_safe(**args),
    emoji="𝕏",
    max_result_size_chars=MAX_RESULT_CHARS,
)
