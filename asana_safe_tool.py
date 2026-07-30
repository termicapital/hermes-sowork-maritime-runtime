#!/usr/bin/env python3
"""Restricted read-only Asana tool; the raw token remains in the parent runtime."""

from __future__ import annotations

from tools.registry import registry
from safe_proxy_client import proxy


ACTIONS = {
    "get_me",
    "list_projects",
    "get_project",
    "list_sections",
    "list_tasks",
    "get_task",
    "search_tasks",
}


def asana_read(
    action: str,
    project_gid: str = "",
    task_gid: str = "",
    query: str = "",
    limit: int = 50,
) -> str:
    action = str(action).strip()
    project_gid = str(project_gid).strip()
    task_gid = str(task_gid).strip()
    query = str(query).strip()
    limit = int(limit)
    if action not in ACTIONS:
        raise ValueError("unsupported read action")
    if action in {"get_project", "list_sections", "list_tasks"} and not project_gid:
        raise ValueError("project_gid is required for this action")
    if action == "get_task" and not task_gid:
        raise ValueError("task_gid is required for this action")
    if action == "search_tasks" and not query:
        raise ValueError("query is required for search_tasks")
    if len(query) > 200:
        raise ValueError("query exceeds 200 characters")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    payload = {
        "action": action,
        "project_gid": project_gid,
        "task_gid": task_gid,
        "query": query,
        "limit": limit,
    }
    return proxy("/internal/asana/read", payload, timeout=60)


SCHEMA = {
    "name": "asana_read",
    "description": (
        "Read the approved Suhail Asana workspace through a parent-held credential. "
        "Supports account, projects, sections, tasks, and task search. This tool is "
        "strictly read-only: it cannot create, update, assign, move, or complete tasks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": sorted(ACTIONS)},
            "project_gid": {"type": "string", "pattern": "^[0-9]{1,32}$"},
            "task_gid": {"type": "string", "pattern": "^[0-9]{1,32}$"},
            "query": {"type": "string", "maxLength": 200},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}

registry.register(
    name="asana_read",
    toolset="asana_safe",
    schema=SCHEMA,
    handler=lambda args, **_kwargs: asana_read(
        args.get("action", ""),
        args.get("project_gid", ""),
        args.get("task_gid", ""),
        args.get("query", ""),
        args.get("limit", 50),
    ),
    emoji="📋",
    max_result_size_chars=90_000,
)
