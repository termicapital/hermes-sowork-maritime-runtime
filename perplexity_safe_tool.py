"""Bounded Perplexity search/chat child tool."""

from tools.registry import registry
from safe_proxy_client import MAX_RESULT_CHARS, proxy


def perplexity_safe(
    action, query="", prompt="", model="sonar", max_tokens=1200, limit=10
):
    return proxy(
        "/internal/perplexity",
        {
            "action": action,
            "query": query,
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
            "limit": limit,
        },
        timeout=1700 if model == "sonar-deep-research" else 300,
    )


SCHEMA = {
    "name": "perplexity_safe",
    "description": "Bounded Perplexity search or chat. Models: sonar, sonar-pro, sonar-reasoning-pro, sonar-deep-research. Full discovery runs use bounded direct Perplexity, same-model OpenRouter, and independent OpenAI + Exa web-research fallback stages.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["search", "chat"]},
            "query": {"type": "string", "maxLength": 500},
            "prompt": {"type": "string", "maxLength": 12000},
            "model": {
                "type": "string",
                "enum": [
                    "sonar",
                    "sonar-pro",
                    "sonar-reasoning-pro",
                    "sonar-deep-research",
                ],
            },
            "max_tokens": {"type": "integer", "minimum": 1, "maximum": 4000},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}
registry.register(
    name="perplexity_safe",
    toolset="perplexity_safe",
    schema=SCHEMA,
    handler=lambda args, **_: perplexity_safe(**args),
    emoji="🔎",
    max_result_size_chars=MAX_RESULT_CHARS,
)
