#!/bin/sh
set -eu

PERSISTENT_HOME=/data/hermes
mkdir -p "$PERSISTENT_HOME"
chown 10000:10000 "$PERSISTENT_HOME"
chmod 0700 "$PERSISTENT_HOME"

# Maritime starts custom images as root even when Docker USER is set. Drop
# privileges explicitly after preparing only this agent's persistent subtree.
exec /usr/bin/setpriv \
  --reuid=10000 \
  --regid=10000 \
  --init-groups \
  --bounding-set=-all \
  --no-new-privs \
  /opt/hermes/.venv/bin/python /opt/discovery-runtime/discovery_runtime.py
