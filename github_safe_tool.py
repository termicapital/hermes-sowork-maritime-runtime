"""Safe exact-repository GitHub child tool."""

from tools.registry import registry
from safe_proxy_client import MAX_RESULT_CHARS, proxy


def github_safe(action, repo, **kwargs):
    return proxy("/internal/github", {"action": action, "repo": repo, **kwargs})


SCHEMA = {
    "name": "github_safe",
    "description": "Bounded GitHub reads and agent/* branch file/PR writes for exactly termicapital/discovery-scout and termicapital/hermes-sowork-maritime-runtime. Never force, merge, mutate workflows/settings/secrets/releases, or write main/master/default.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "repo",
                    "branches",
                    "file",
                    "commits",
                    "issues",
                    "prs",
                    "checks",
                    "workflows",
                    "prepare_write",
                    "create_branch",
                    "upsert_file",
                    "delete_file",
                    "open_pr",
                    "update_pr",
                ],
            },
            "write_action": {
                "type": "string",
                "enum": [
                    "create_branch",
                    "upsert_file",
                    "delete_file",
                    "open_pr",
                    "update_pr",
                ],
            },
            "repo": {
                "type": "string",
                "enum": [
                    "termicapital/discovery-scout",
                    "termicapital/hermes-sowork-maritime-runtime",
                ],
            },
            "branch": {"type": "string", "maxLength": 200},
            "base": {"type": "string", "maxLength": 200},
            "path": {"type": "string", "maxLength": 500},
            "content": {"type": "string", "maxLength": 40000},
            "message": {"type": "string", "maxLength": 500},
            "sha": {"type": "string", "maxLength": 64},
            "title": {"type": "string", "maxLength": 200},
            "body": {"type": "string", "maxLength": 10000},
            "number": {"type": "integer", "minimum": 1},
            "state": {"type": "string", "enum": ["open", "closed"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
        "required": ["action", "repo"],
        "additionalProperties": False,
    },
}
registry.register(
    name="github_safe",
    toolset="github_safe",
    schema=SCHEMA,
    handler=lambda args, **_: github_safe(**args),
    emoji="🐙",
    max_result_size_chars=MAX_RESULT_CHARS,
)
