"""Bounded Firecrawl v2 search/scrape child tool."""

from tools.registry import registry
from safe_proxy_client import MAX_RESULT_CHARS, proxy


def firecrawl_safe(
    action,
    query="",
    limit=5,
    country="",
    include_domains=None,
    exclude_domains=None,
    hydrate_markdown=False,
    url="",
    only_main_content=True,
    proxy_mode="auto",
):
    payload = {"action": action}
    if action == "search":
        payload.update(
            {
                "query": query,
                "limit": limit,
                "country": country,
                "include_domains": include_domains or [],
                "exclude_domains": exclude_domains or [],
                "hydrate_markdown": hydrate_markdown,
            }
        )
    else:
        payload.update(
            {"url": url, "only_main_content": only_main_content, "proxy": proxy_mode}
        )
    return proxy("/internal/firecrawl", payload)


SCHEMA = {
    "name": "firecrawl_safe",
    "description": "Search via fixed Firecrawl v2 search or scrape one public URL. No headers/actions/JS. Search supports include OR exclude domains and optional markdown hydration.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["search", "scrape"]},
            "query": {"type": "string", "maxLength": 500},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            "country": {"type": "string", "maxLength": 2},
            "include_domains": {
                "type": "array",
                "maxItems": 20,
                "items": {"type": "string"},
            },
            "exclude_domains": {
                "type": "array",
                "maxItems": 20,
                "items": {"type": "string"},
            },
            "hydrate_markdown": {"type": "boolean"},
            "url": {"type": "string", "maxLength": 2048},
            "only_main_content": {"type": "boolean"},
            "proxy_mode": {"type": "string", "enum": ["basic", "enhanced", "auto"]},
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}
registry.register(
    name="firecrawl_safe",
    toolset="firecrawl_safe",
    schema=SCHEMA,
    handler=lambda args, **_: firecrawl_safe(**args),
    emoji="🔥",
    max_result_size_chars=MAX_RESULT_CHARS,
)
