#!/bin/sh
set -eu

/opt/hermes/.venv/bin/hermes --version
test "$(id -u)" = "10000"
test "${HERMES_HOME:-}" = "/data/hermes"
test -d /data/hermes
test ! -e /data/hermes/.env
PYTHONPATH=/opt/hermes /opt/hermes/.venv/bin/python - <<'PY'
from toolsets import resolve_toolset
assert set(resolve_toolset('skills_readonly')) == {'skills_list', 'skill_view'}
assert set(resolve_toolset('openrouter_safe')) == {'openrouter_catalog', 'openrouter_generate'}
assert set(resolve_toolset('firecrawl_safe')) == {'firecrawl_safe'}
assert set(resolve_toolset('perplexity_safe')) == {'perplexity_safe'}
assert set(resolve_toolset('xai_safe')) == {'xai_safe'}
assert set(resolve_toolset('github_safe')) == {'github_safe'}
assert set(resolve_toolset('asana_safe')) == {'asana_read'}
assert set(resolve_toolset('sowork_meetings_safe')) == {'sowork_meetings_read'}
print('skills_readonly', resolve_toolset('skills_readonly'))
PY
/opt/hermes/.venv/bin/python - <<'PY'
import json, os, urllib.request
required = [
    'SOWORK_CHANNEL_ID', 'SOWORK_ALLOWED_USER_IDS', 'SOWORK_API_TOKEN',
    'HERMES_CODEX_AUTH_B64', 'OPENROUTER_API_KEY', 'ASANA_TOKEN',
    'FIRECRAWL_API_KEY', 'XAI_API_KEY', 'PERPLEXITY_API_KEY', 'GITHUB_TOKEN',
    'GITHUB_WRITE_ALLOWED_USER_IDS', 'DISCOVERY_PUBLIC_BASE_URL'
]
present = {key: bool(os.getenv(key, '').strip()) for key in required}
print(json.dumps({'env_present': present}))
missing = [key for key, configured in present.items() if not configured]
assert not missing, 'missing required runtime environment: ' + ', '.join(missing)
with urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=10) as response:
    health = json.loads(response.read().decode())
print(json.dumps(health))
assert health.get('status') == 'ok', health
assert health.get('capabilities_ready') is True, health
PY
/opt/hermes/.venv/bin/hermes skills list | tail -5
