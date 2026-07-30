"""Shared bounded loopback client for Discovery child tools."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

MAX_RESULT_CHARS = 200_000


def proxy(
    path: str,
    payload: dict[str, Any],
    timeout: int = 300,
    max_request_bytes: int = 64_000,
) -> str:
    if not path.startswith("/internal/") or "://" in path:
        raise ValueError("invalid internal route")
    if not 1 <= max_request_bytes <= 200_000:
        raise ValueError("invalid request bound")
    raw = json.dumps(payload, separators=(",", ":")).encode()
    if len(raw) > max_request_bytes:
        raise ValueError("request exceeds configured bound")
    token_path = os.environ.get("HERMES_RUN_CAPABILITY_PATH", "")
    if not token_path:
        raise RuntimeError("run capability is unavailable")
    token = Path(token_path).read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise RuntimeError("run capability is invalid")
    request = urllib.request.Request(
        "http://127.0.0.1:8765" + path,
        data=raw,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Discovery-Run-Capability": token,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = response.read(MAX_RESULT_CHARS + 1)
    if len(result) > MAX_RESULT_CHARS:
        raise RuntimeError("proxy response exceeded 200 KB")
    parsed = json.loads(result.decode("utf-8"))
    encoded = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > MAX_RESULT_CHARS:
        raise RuntimeError("proxy result exceeded 200,000 characters")
    return encoded
