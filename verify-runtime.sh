#!/bin/sh
set -eu

/opt/hermes/.venv/bin/hermes --version
test ! -e /opt/data/.env
PYTHONPATH=/opt/hermes /opt/hermes/.venv/bin/python - <<'PY'
from toolsets import resolve_toolset
assert resolve_toolset('skills_readonly') == ['skills_list', 'skill_view']
print('skills_readonly', resolve_toolset('skills_readonly'))
PY
/opt/hermes/.venv/bin/python - <<'PY'
import json, os, urllib.request
required = [
    'SOWORK_CHANNEL_ID', 'SOWORK_ALLOWED_USER_IDS', 'SOWORK_API_TOKEN',
    'HERMES_CODEX_AUTH_B64', 'OPENROUTER_API_KEY'
]
print(json.dumps({'env_present': {key: bool(os.getenv(key)) for key in required}}))
with urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=10) as response:
    print(response.read().decode())
PY
/opt/hermes/.venv/bin/hermes skills list | tail -5
