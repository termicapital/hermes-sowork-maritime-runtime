#!/usr/bin/env python3
"""Install a read-only skills toolset into the pinned Hermes image source."""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = '    "skills": {'
BLOCK = '''    "skills_readonly": {
        "description": "Read-only access to installed skill documents",
        "tools": ["skills_list", "skill_view"],
        "includes": []
    },

    "openrouter_safe": {
        "description": "Restricted OpenRouter queries through a parent-held credential",
        "tools": ["openrouter_query"],
        "includes": []
    },

'''


def patch_source(source: str) -> str:
    has_readonly = '"skills_readonly"' in source
    has_openrouter = '"openrouter_safe"' in source
    if has_readonly and has_openrouter:
        return source
    if has_readonly or has_openrouter:
        raise RuntimeError("Hermes toolsets.py has a partial Discovery runtime patch")
    if MARKER not in source:
        raise RuntimeError("Pinned Hermes toolsets.py no longer has the expected skills marker")
    return source.replace(MARKER, BLOCK + MARKER, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    source = args.path.read_text(encoding="utf-8")
    patched = patch_source(source)
    args.path.write_text(patched, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
