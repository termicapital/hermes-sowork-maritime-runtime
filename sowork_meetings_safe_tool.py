#!/usr/bin/env python3
"""Restricted read-only SoWork Meeting Library tool."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from tools.registry import registry

ENDPOINT = "http://127.0.0.1:8765/internal/sowork/meetings/read"
TOKEN_PATH = Path("/data/hermes/discovery-runtime/openrouter-proxy-token")
ACTIONS = {"list_meetings", "search_meetings", "get_meeting"}
DIGEST_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
KINDS = {"all", "title", "note", "transcript", "chat"}


def sowork_meetings_read(
    action: str,
    digest_id: str = "",
    query: str = "",
    kind: str = "all",
    since: int = 0,
    until: int = 0,
    limit: int = 20,
) -> str:
    action = str(action).strip()
    digest_id = str(digest_id).strip()
    query = str(query).strip()
    kind = str(kind).strip().lower() or "all"
    since = int(since)
    until = int(until)
    limit = int(limit)
    if action not in ACTIONS:
        raise ValueError("unsupported meeting-library action")
    if action == "get_meeting" and not DIGEST_RE.fullmatch(digest_id):
        raise ValueError("valid digest_id required")
    if action == "search_meetings" and (not query or len(query) > 256):
        raise ValueError("query must contain 1 to 256 characters")
    if kind not in KINDS:
        raise ValueError("unsupported search kind")
    if since < 0 or until < 0 or (since and until and since > until):
        raise ValueError("invalid time range")
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    body = json.dumps({
        "action": action,
        "digest_id": digest_id,
        "query": query,
        "kind": kind,
        "since": since,
        "until": until,
        "limit": limit,
    }).encode("utf-8")
    capability = TOKEN_PATH.read_text(encoding="utf-8").strip()
    if len(capability) < 32:
        raise RuntimeError("SoWork meetings proxy capability is unavailable")
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Discovery-Internal-Token": capability,
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw_response = response.read(250_001)
    if len(raw_response) > 250_000:
        raise RuntimeError("SoWork meetings proxy response exceeded 250 KB")
    payload = json.loads(raw_response.decode("utf-8"))
    return json.dumps(payload, ensure_ascii=False)


SCHEMA = {
    "name": "sowork_meetings_read",
    "description": (
        "Read ended meetings accessible through the approved SoWork Meeting Library. "
        "List or search meetings and retrieve API-exposed notes, transcripts, and "
        "captured meeting chat. This tool is strictly read-only and never returns video URLs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": sorted(ACTIONS)},
            "digest_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,128}$"},
            "query": {"type": "string", "maxLength": 256},
            "kind": {"type": "string", "enum": sorted(KINDS), "default": "all"},
            "since": {"type": "integer", "minimum": 0, "default": 0},
            "until": {"type": "integer", "minimum": 0, "default": 0},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        },
        "required": ["action"],
        "additionalProperties": False,
    },
}

registry.register(
    name="sowork_meetings_read",
    toolset="sowork_meetings_safe",
    schema=SCHEMA,
    handler=lambda args, **_kwargs: sowork_meetings_read(
        args.get("action", ""),
        args.get("digest_id", ""),
        args.get("query", ""),
        args.get("kind", "all"),
        args.get("since", 0),
        args.get("until", 0),
        args.get("limit", 20),
    ),
    emoji="🗒️",
    max_result_size_chars=220_000,
)
