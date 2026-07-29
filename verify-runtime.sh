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
assert set(resolve_toolset('openrouter_safe')) == {'openrouter_query'}
assert set(resolve_toolset('asana_safe')) == {'asana_read'}
assert set(resolve_toolset('sowork_meetings_safe')) == {'sowork_meetings_read'}
print('skills_readonly', resolve_toolset('skills_readonly'))
PY
/opt/hermes/.venv/bin/python - <<'PY'
import json, os, urllib.request
required = [
    'SOWORK_CHANNEL_ID', 'SOWORK_ALLOWED_USER_IDS', 'SOWORK_API_TOKEN',
    'HERMES_CODEX_AUTH_B64', 'OPENROUTER_API_KEY', 'ASANA_TOKEN'
]
print(json.dumps({'env_present': {key: bool(os.getenv(key)) for key in required}}))
with urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=10) as response:
    print(response.read().decode())
PY
/opt/hermes/.venv/bin/hermes skills list | tail -5
