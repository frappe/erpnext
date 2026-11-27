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
    # The helper shell expands the token when git invokes it, not when this script exports it.
    # shellcheck disable=SC2016
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

# Both jobs use the Pilot CLI. Site setup only needs the database and Redis.
if [ "$DB" = postgres ] && ! command -v uv >/dev/null; then
    curl -fsSL https://astral.sh/uv/install.sh | sh
fi
if [ "$DB" = postgres ] && ! command -v redis-server >/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq redis-server
fi
mkdir -p "$HOME/pilot"
curl -fsSL https://github.com/frappe/pilot/releases/download/v1.0.0-rc.5/pilot.tar.gz \
    | tar -xz -C "$HOME/pilot"

pilot new frappe-bench --frappe-branch "$frappebranch" --database "$DB" --admin-password 'PilotAdmin123!'
pilot -b frappe-bench set-bench-config python "$(command -v python)"
pilot -b frappe-bench set-bench-config admin_allow_site_to_pilot_communication false
pilot -b frappe-bench set-bench-config watch_apps_js false
pilot -b frappe-bench set-bench-config "${DB}_existing" true
pilot -b frappe-bench set-bench-config "${DB}_host" 127.0.0.1
if [ "$DB" = postgres ]; then
    pilot -b frappe-bench set-bench-config postgres_port 5432
    pilot -b frappe-bench set-bench-config postgres_admin_user postgres
    pilot -b frappe-bench set-bench-config postgres_password travis
else
    pilot -b frappe-bench set-bench-config mariadb_port 3306
    pilot -b frappe-bench set-bench-config mariadb_admin_user root
    pilot -b frappe-bench set-bench-config mariadb_password root
fi
pilot -b frappe-bench init --skip-frontend
if [ "$DB" = postgres ]; then
    if ! command -v wkhtmltopdf >/dev/null; then
        wget -qO /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
        sudo apt-get install -y -qq /tmp/wkhtmltox.deb
    fi
    pilot -b frappe-bench frappe setup-chrome
fi

printf '[client]\nskip-ssl\n' > "$HOME/.my.cnf"
cd "$HOME/pilot/benches/frappe-bench"

git config --global --add safe.directory "$GITHUB_WORKSPACE"
git config --global --add safe.directory "$GITHUB_WORKSPACE/.git"

erpnext_branch=${GITHUB_REF_NAME:-$(git -C "$GITHUB_WORKSPACE" branch --show-current)}
erpnext_commit=${GITHUB_SHA:-$(git -C "$GITHUB_WORKSPACE" rev-parse HEAD)}
if [ "$DB" = postgres ]; then
    pilot get-app https://github.com/frappe/payments --branch develop --skip-assets
fi
pilot get-app "$GITHUB_WORKSPACE" --branch "$erpnext_branch" --commit "$erpnext_commit" --skip-assets

if [ "$DB" = mariadb ]; then
    mkdir -p sites/test_site
    jq 'del(.install_apps)' "$GITHUB_WORKSPACE/.github/helper/site_config_mariadb.json" > sites/test_site/site_config.json
    printf 'frappe\nerpnext\n' > sites/apps.txt
    mariadb -h 127.0.0.1 -u root -proot <<'SQL'
SET GLOBAL character_set_server = 'utf8mb4', GLOBAL collation_server = 'utf8mb4_unicode_ci';
CREATE USER 'test_frappe'@'%' IDENTIFIED BY 'test_frappe';
CREATE DATABASE test_frappe;
GRANT ALL PRIVILEGES ON test_frappe.* TO 'test_frappe'@'%';
SQL
    exit 0
fi

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

defaults = Path(os.environ["GITHUB_WORKSPACE"]) / ".github/helper/site_config_postgres.json"
site = Path("sites/test_site/site_config.json")
settings = json.loads(defaults.read_text())
for key in ("db_name", "db_password", "install_apps"):
    settings.pop(key)
settings.update(json.loads(site.read_text()))
settings["allow_tests"] = True
site.write_text(json.dumps(settings, indent=2) + "\n")
PYTHON
