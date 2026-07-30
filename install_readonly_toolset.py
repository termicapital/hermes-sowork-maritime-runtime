#!/usr/bin/env python3
"""Install a read-only skills toolset into the pinned Hermes image source."""

from __future__ import annotations

import argparse
from pathlib import Path

MARKER = '    "skills": {'
BLOCK = """    "skills_readonly": {
        "description": "Read-only access to installed skill documents",
        "tools": ["skills_list", "skill_view"],
        "includes": []
    },

    "openrouter_safe": {
        "description": "Live OpenRouter catalog and human-model-gated text/image/audio generation",
        "tools": ["openrouter_catalog", "openrouter_generate"],
        "includes": []
    },

    "firecrawl_safe": {
        "description": "Restricted Firecrawl v2 search and public URL scrape",
        "tools": ["firecrawl_safe"],
        "includes": []
    },

    "perplexity_safe": {
        "description": "Bounded Perplexity search and sonar chat",
        "tools": ["perplexity_safe"],
        "includes": []
    },

    "xai_safe": {
        "description": "Bounded xAI Responses web and X research",
        "tools": ["xai_safe"],
        "includes": []
    },

    "github_safe": {
        "description": "Exact-repository GitHub reads and agent branch/PR writes",
        "tools": ["github_safe"],
        "includes": []
    },

    "asana_safe": {
        "description": "Read-only Asana access through a parent-held credential",
        "tools": ["asana_read"],
        "includes": []
    },

    "notion_safe": {
        "description": "Bounded Discovery Notion access through a parent-held credential",
        "tools": ["notion_safe"],
        "includes": []
    },

    "sowork_meetings_safe": {
        "description": "Read-only SoWork Meeting Library access through the parent bridge",
        "tools": ["sowork_meetings_read"],
        "includes": []
    },

"""

TOOLSET_NAMES = {
    "skills_readonly",
    "openrouter_safe",
    "firecrawl_safe",
    "perplexity_safe",
    "xai_safe",
    "github_safe",
    "asana_safe",
    "notion_safe",
    "sowork_meetings_safe",
}


def patch_source(source: str) -> str:
    present = {name for name in TOOLSET_NAMES if f'"{name}"' in source}
    if present == TOOLSET_NAMES:
        return source
    if present:
        raise RuntimeError("Hermes toolsets.py has a partial Discovery runtime patch")
    if MARKER not in source:
        raise RuntimeError(
            "Pinned Hermes toolsets.py no longer has the expected skills marker"
        )
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
