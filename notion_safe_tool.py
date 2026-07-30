#!/usr/bin/env python3
"""Restricted Notion tool; the raw token remains in the parent runtime."""

from __future__ import annotations

from typing import Any

from safe_proxy_client import proxy
from tools.registry import registry

ACTIONS = {"get_schema", "query", "fetch_page", "fetch_blocks", "create_page"}
DATA_SOURCES = {"problem_signal", "discovery_pipeline"}
CURSOR_MAX = 10_000


def notion_safe(
    action: str,
    data_source: str = "",
    page_id: str = "",
    filter: dict[str, Any] | None = None,
    sorts: list[dict[str, Any]] | None = None,
    page_size: int = 100,
    start_cursor: str = "",
    properties: dict[str, Any] | None = None,
    content: str = "",
    block_id: str = "",
) -> str:
    action = str(action).strip()
    data_source = str(data_source).strip()
    page_id = str(page_id).strip()
    block_id = str(block_id).strip()
    page_size = int(page_size)
    if not isinstance(start_cursor, str):
        raise ValueError("start_cursor must be a string")
    content = str(content)
    if action not in ACTIONS:
        raise ValueError("unsupported Notion action")
    if (
        action in {"get_schema", "query", "create_page"}
        and data_source not in DATA_SOURCES
    ):
        raise ValueError("approved data_source alias required")
    if action == "fetch_page" and not page_id:
        raise ValueError("page_id is required")
    if action == "fetch_blocks" and not block_id:
        raise ValueError("block_id is required")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
    if len(start_cursor) > CURSOR_MAX:
        raise ValueError(f"start_cursor exceeds {CURSOR_MAX:,} characters")
    if not isinstance(filter or {}, dict) or not isinstance(sorts or [], list):
        raise ValueError("filter and sorts have invalid types")
    if not isinstance(properties or {}, dict):
        raise ValueError("properties must be an object")
    if len(content) > 80_000:
        raise ValueError("content exceeds 80,000 characters")
    if action == "create_page" and not properties:
        raise ValueError("properties are required for create_page")

    payload = {
        "action": action,
        "data_source": data_source,
        "page_id": page_id,
        "block_id": block_id,
        "filter": filter or {},
        "sorts": sorts or [],
        "page_size": page_size,
        "start_cursor": start_cursor,
        "properties": properties or {},
        "content": content,
    }
    return proxy(
        "/internal/notion",
        payload,
        timeout=180,
        max_request_bytes=200_000,
    )


SCHEMA = {
    "name": "notion_safe",
    "description": (
        "Read the approved Discovery Pipeline and Problem Signal Capture data sources, "
        "fetch approved pipeline pages, and create quality-gated autonomous-run rows. "
        "The credential remains parent-side. create_page is admitted only for an explicit "
        "--autonomous owner run; no update, delete, schema, or workspace-wide operations exist."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": sorted(ACTIONS)},
            "data_source": {"type": "string", "enum": sorted(DATA_SOURCES)},
            "page_id": {"type": "string", "maxLength": 100},
            "block_id": {"type": "string", "maxLength": 100},
            "filter": {"type": "object"},
            "sorts": {"type": "array", "items": {"type": "object"}, "maxItems": 10},
            "page_size": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 100,
            },
            "start_cursor": {"type": "string", "maxLength": CURSOR_MAX},
            "properties": {"type": "object"},
            "content": {"type": "string", "maxLength": 80000},
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}

registry.register(
    name="notion_safe",
    toolset="notion_safe",
    schema=SCHEMA,
    handler=lambda args, **_kwargs: notion_safe(
        args.get("action", ""),
        args.get("data_source", ""),
        args.get("page_id", ""),
        args.get("filter"),
        args.get("sorts"),
        args.get("page_size", 100),
        args.get("start_cursor", ""),
        args.get("properties"),
        args.get("content", ""),
        args.get("block_id", ""),
    ),
    emoji="🗂️",
    max_result_size_chars=200_000,
)
