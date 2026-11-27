#!/bin/bash

set -eo pipefail

export PATH="$HOME/pilot/bin:$HOME/.local/bin:$PATH"
export UV_PYTHON="${UV_PYTHON:-3.14}"

ci_github_token=${CI_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}
if [ -n "$ci_github_token" ]; then
    export CI_GITHUB_TOKEN="$ci_github_token"
    export GIT_CONFIG_COUNT=3
    export GIT_CONFIG_KEY_0="credential.helper"
    export GIT_CONFIG_VALUE_0=""
    export GIT_CONFIG_KEY_1="credential.https://github.com.username"
    export GIT_CONFIG_VALUE_1="x-access-token"
    export GIT_CONFIG_KEY_2="credential.https://github.com.helper"
    export GIT_CONFIG_VALUE_2='!f() { test "$1" = get && echo "password=$CI_GITHUB_TOKEN"; }; f'
fi
export GIT_TERMINAL_PROMPT=0

frappeuser=${FRAPPE_USER:-frappe}
frappebranch=${FRAPPE_BRANCH:-develop}
probe=0
git ls-remote --exit-code --heads "https://github.com/${frappeuser}/frappe" "$frappebranch" >/dev/null 2>&1 || probe=$?
if [ "$probe" -eq 2 ]; then
    echo "frappe has no branch ${frappebranch}, falling back to develop"
    frappebranch=develop
elif [ "$probe" -ne 0 ]; then
    echo "could not reach frappe to check branch ${frappebranch} (git ls-remote exited ${probe})"
    exit "$probe"
fi

mkdir -p "$HOME/pilot"
curl -fsSL https://github.com/frappe/pilot/releases/download/v1.0.0-rc.5/pilot.tar.gz \
    | tar -xz -C "$HOME/pilot"

pilot new frappe-bench --frappe-branch "$frappebranch" --admin-password 'PilotAdmin123!'
pilot -b frappe-bench set-bench-config python "$(command -v python)"
pilot -b frappe-bench set-bench-config admin_allow_site_to_pilot_communication false
pilot -b frappe-bench set-bench-config watch_apps_js false
pilot -b frappe-bench set-bench-config mariadb_existing true
pilot -b frappe-bench set-bench-config mariadb_host 127.0.0.1
pilot -b frappe-bench set-bench-config mariadb_port 3306
pilot -b frappe-bench set-bench-config mariadb_admin_user root
pilot -b frappe-bench set-bench-config mariadb_password root
pilot -b frappe-bench init --skip-frontend
pilot -b frappe-bench frappe setup-chrome

printf '[client]\nskip-ssl\n' > "$HOME/.my.cnf"
cd "$HOME/pilot/benches/frappe-bench"

pilot get-app https://github.com/frappe/payments --branch develop --skip-assets

git config --global --add safe.directory "$GITHUB_WORKSPACE"
git config --global --add safe.directory "$GITHUB_WORKSPACE/.git"

erpnext_branch=${GITHUB_REF_NAME:-$(git -C "$GITHUB_WORKSPACE" branch --show-current)}
erpnext_commit=${GITHUB_SHA:-$(git -C "$GITHUB_WORKSPACE" rev-parse HEAD)}
pilot get-app "$GITHUB_WORKSPACE" --branch "$erpnext_branch" --commit "$erpnext_commit" --skip-assets

uv pip install --python env/bin/python -e "apps/frappe[test]"

redis-server config/redis_cache.conf --daemonize yes
redis-server config/redis_queue.conf --daemonize yes
read -r cache_port queue_port < <(python -c 'import tomllib; r = tomllib.load(open("bench.toml", "rb"))["redis"]; print(r["cache_port"], r["queue_port"])')
for port in "$cache_port" "$queue_port"; do
    redis-cli -p "$port" ping | grep -qx PONG
done

if [ ! -f sites/assets/assets.json ]; then
    mkdir -p sites/assets
    printf '{}\n' > sites/assets/assets.json
fi
pilot build --apps frappe payments erpnext
pilot new-site test_site --admin-password admin --apps frappe payments erpnext --skip-assets

python - <<'PYTHON'
import json
import os
from pathlib import Path

defaults = Path(os.environ["GITHUB_WORKSPACE"]) / ".github/helper/site_config_mariadb.json"
site = Path("sites/test_site/site_config.json")
settings = json.loads(defaults.read_text())
for key in ("db_name", "db_password", "install_apps"):
    settings.pop(key)
settings.update(json.loads(site.read_text()))
settings["allow_tests"] = True
site.write_text(json.dumps(settings, indent=2) + "\n")
PYTHON

cat > Procfile <<'EOF'
redis_cache: redis-server config/redis_cache.conf
redis_queue: redis-server config/redis_queue.conf
web: cd sites && "$BENCH_PATH/env/bin/python" -m frappe.utils.bench_helper frappe serve --port 8000
worker: (cd sites && "$BENCH_PATH/env/bin/python" -m frappe.utils.bench_helper frappe worker) >> logs/worker.log 2>&1
EOF
