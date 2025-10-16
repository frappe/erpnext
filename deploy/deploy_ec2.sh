#!/usr/bin/env bash
# Simple deploy helper to run on the EC2 instance. It extracts the artifact,
# moves files into place, installs python dependencies (if needed), and restarts
# services. Modify according to your server layout and service manager.

set -euo pipefail

ARTIFACT_PATH="$1"
REMOTE_DIR="$2"

if [ -z "$ARTIFACT_PATH" ] || [ -z "$REMOTE_DIR" ]; then
  echo "Usage: $0 /tmp/erpnext-YYYY.tar.gz /opt/erpnext"
  exit 2
fi

echo "Deploying $ARTIFACT_PATH to $REMOTE_DIR"

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "Extracting artifact to $TMPDIR"
tar -xzf "$ARTIFACT_PATH" -C "$TMPDIR"

echo "Creating remote directory $REMOTE_DIR if missing"
sudo mkdir -p "$REMOTE_DIR"
sudo chown $(whoami):$(whoami) "$REMOTE_DIR"

echo "Syncing files to $REMOTE_DIR"
rsync -av --delete "$TMPDIR/" "$REMOTE_DIR/"

echo "(Optional) Install Python deps"
if [ -f "$REMOTE_DIR/pyproject.toml" ]; then
  if command -v pip >/dev/null 2>&1; then
    python -m pip install --upgrade pip
    python -m pip install -r <(python - <<PY
import tomllib,sys
with open('pyproject.toml','rb') as f:
    data=tomllib.load(f)
reqs = data.get('project',{}).get('dependencies') or []
for r in reqs:
    print(r)
PY
)
  fi
fi

echo "Restarting services (if systemd unit 'erpnext' exists)"
if systemctl list-unit-files | grep -q erpnext; then
  sudo systemctl restart erpnext
  sudo systemctl status erpnext --no-pager || true
else
  echo "No erpnext systemd service found; you may need to restart your webserver/process manager manually."
fi

echo "Deployment finished"
