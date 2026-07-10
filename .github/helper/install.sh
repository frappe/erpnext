#!/bin/bash

set -e

cd ~ || exit

githubbranch=${GITHUB_BASE_REF:-${GITHUB_REF##*/}}
frappeuser=${FRAPPE_USER:-"frappe"}
frappecommitish=${FRAPPE_BRANCH:-$githubbranch}
db_host=${DB_HOST:-"127.0.0.1"}
db_user_host=${DB_USER_HOST:-"localhost"}
wkhtmltox_deb=${WKHTMLTOX_DEB:-"/tmp/wkhtmltox.deb"}
bench_cache_dir=${BENCH_CACHE_DIR:-}

run_as_ci_user_if_needed() {
    if [ "$(id -u)" != "0" ] || [ "${SKIP_SYSTEM_SETUP:-0}" != "1" ] || [ "${ERPNEXT_CI_NON_ROOT:-0}" = "1" ]; then
        return
    fi

    local missing_packages=()
    if ! command -v pkg-config >/dev/null 2>&1; then
        missing_packages+=("pkg-config")
    fi
    if ! command -v mariadb_config >/dev/null 2>&1 && ! command -v mysql_config >/dev/null 2>&1; then
        missing_packages+=("libmariadb-dev")
    fi
    if ! command -v crontab >/dev/null 2>&1; then
        missing_packages+=("cron")
    fi

    if [ "${#missing_packages[@]}" -gt 0 ]; then
        apt-get update
        apt-get install -y --no-install-recommends "${missing_packages[@]}"
    fi

    local ci_user="${ERPNEXT_CI_USER:-frappe}"

    if ! id "$ci_user" >/dev/null 2>&1; then
        useradd --home-dir "$HOME" --no-create-home --shell /bin/bash "$ci_user"
    fi

    rm -rf ~/frappe ~/frappe-bench

    local ci_dirs=(
        "$HOME"
        "$GITHUB_WORKSPACE"
        "$HOME/.cache"
        "${PIP_CACHE_DIR:-$HOME/.cache/pip}"
        "${npm_config_cache:-$HOME/.npm}"
        "${YARN_CACHE_FOLDER:-$HOME/.cache/yarn}"
        "$HOME/.yarn"
        "${UV_CACHE_DIR:-$HOME/.cache/uv}"
        "$(dirname "$wkhtmltox_deb")"
    )
    if [ -n "$bench_cache_dir" ]; then
        ci_dirs+=("$bench_cache_dir")
    fi

    # Create + own (non-recursively) the home/cache/workspace dirs before dropping to
    # the ci user. We deliberately do NOT wipe the yarn/uv caches here so a persistent
    # cache (mounted volume or baked image layer) stays warm across runs.
    mkdir -p "${ci_dirs[@]}" "$HOME/.yarn"
    chown "$ci_user:$ci_user" "${ci_dirs[@]}" "$HOME/.yarn"

    export ERPNEXT_CI_NON_ROOT=1
    exec su -m "$ci_user" -s /bin/bash -c "cd '$HOME' && bash '$GITHUB_WORKSPACE/.github/helper/install.sh'"
}

run_as_ci_user_if_needed

run_ci_step() {
    local label=$1
    shift

    echo "::group::${label}"
    date -u
    local exit_code=0
    timeout --foreground "${CI_INSTALL_STEP_TIMEOUT:-1800}" "$@" || exit_code=$?
    date -u
    echo "::endgroup::"
    return "$exit_code"
}

if [ -n "${GITHUB_WORKSPACE:-}" ]; then
    git config --global --add safe.directory "$GITHUB_WORKSPACE" || true
    git config --global --add safe.directory "$GITHUB_WORKSPACE/.git" || true
fi

rm -rf ~/frappe ~/frappe-bench

# ---------------------------------------------------------------------------
# Phase 1 — parallelise the three slow, independent setup steps:
#   a) system packages   b) frappe-bench pip install   c) frappe git fetch
# ---------------------------------------------------------------------------

if [ "${SKIP_SYSTEM_SETUP:-0}" != "1" ]; then
    sudo apt-get update

    # apt remove/install must run sequentially but can overlap with pip and git.
    sudo apt-get remove -y mysql-server mysql-client
    sudo apt-get install -y libcups2-dev redis-server mariadb-client libmariadb-dev &
    apt_pid=$!

    pip install frappe-bench &
    pip_pid=$!
else
    apt_pid=
    pip_pid=
fi

mkdir frappe
(
  cd frappe
  git init
  git remote add origin "https://github.com/${frappeuser}/frappe"
  git fetch origin "${frappecommitish}" --depth 1
) &
clone_pid=$!

if [ -n "$apt_pid" ]; then wait $apt_pid; fi
if [ -n "$pip_pid" ]; then wait $pip_pid; fi
wait $clone_pid

pushd frappe
git checkout FETCH_HEAD
popd
frappe_sha=$(git -C frappe rev-parse HEAD)

get_bench_cache_archive() {
    if [ -z "$bench_cache_dir" ]; then
        return
    fi

    mkdir -p "$bench_cache_dir"

    # Keyed on tool versions only (NOT the frappe SHA): any recent base bench works, because
    # restore_warm_bench fast-forwards it to the exact live develop SHA. This is what lets a
    # constantly-moving develop still hit the cache.
    local cache_key
    cache_key=$(
        {
            uname -m
            python --version
            node --version
            bench --version
        } | sha256sum | awk '{print $1}'
    )

    echo "${bench_cache_dir}/frappe-bench-base-${cache_key}.tar.zst"
}

restore_warm_bench() {
    bench_cache_archive=$(get_bench_cache_archive)
    [ -n "$bench_cache_archive" ] && [ -f "$bench_cache_archive" ] || return 1

    echo "Restoring base bench from ${bench_cache_archive}"
    tar --use-compress-program=unzstd -xf "$bench_cache_archive" -C ~ || return 1
    [ -d ~/frappe-bench/apps/frappe/.git ] || return 1
    mkdir -p ~/frappe-bench/sites ~/frappe-bench/logs
    [ -f ~/frappe-bench/sites/apps.txt ] || printf "frappe\n" > ~/frappe-bench/sites/apps.txt
    [ -f ~/frappe-bench/sites/common_site_config.json ] || printf "{}\n" > ~/frappe-bench/sites/common_site_config.json

    # Fast-forward the restored frappe to the EXACT live develop SHA fetched in phase 1, then
    # rebuild only what changed. The editable install means the venv tracks the new code with
    # no reinstall. Any failure returns non-zero so the caller falls back to a full bench init.
    if ! (
        cd ~/frappe-bench/apps/frappe || exit 1
        # Phase 1 already fetched ~/frappe to the exact live develop SHA. Fetch that commit
        # straight from it (bench init names the remote 'upstream', not 'origin', and points
        # it at this local clone — so a plain `git fetch origin` does not work).
        git fetch --no-tags "$HOME/frappe" HEAD || exit 1
        git checkout --force FETCH_HEAD || exit 1
    ); then
        echo "Fast-forward to ${frappe_sha} failed; falling back to full init"
        rm -rf ~/frappe-bench
        return 1
    fi

    # Pick up any frappe dependency changes since the base was built (cached → fast if none),
    # so a develop commit that bumped requirements doesn't leave a stale venv.
    if ! ~/frappe-bench/env/bin/python -m pip install -q -e ~/frappe-bench/apps/frappe; then
        echo "frappe dependency refresh failed; falling back to full init"
        rm -rf ~/frappe-bench
        return 1
    fi

    ( cd ~/frappe-bench && CI=Yes bench build --app frappe ) || { rm -rf ~/frappe-bench; return 1; }
    return 0
}

save_warm_bench() {
    if [ -z "${bench_cache_archive:-}" ] || [ -f "$bench_cache_archive" ]; then
        return
    fi

    if [ -n "$bench_cache_dir" ] && [ ! -w "$bench_cache_dir" ]; then
        echo "Skipping warm bench save because ${bench_cache_dir} is not writable"
        return
    fi

    local tmp_archive
    tmp_archive="${bench_cache_archive}.${$}.tmp"

    echo "Saving warm bench to ${bench_cache_archive}"
    # Keep sites/common_site_config.json (the redis ports live there — dropping it makes the
    # restore path fall back to a default redis port that bench start never bound, so reinstall
    # fails with "redis ... connection refused"). Only the rebuildable sites/assets is excluded;
    # restore_warm_bench runs `bench build` to regenerate it.
    tar \
        --use-compress-program="zstd -T0 -3" \
        --exclude="frappe-bench/logs" \
        --exclude="frappe-bench/sites/assets" \
        -cf "$tmp_archive" \
        -C ~ frappe-bench
    mv "$tmp_archive" "$bench_cache_archive"
}

# ---------------------------------------------------------------------------
# Phase 2 — bench init and site setup
# ---------------------------------------------------------------------------

install_whktml() {
    # Re-use the .deb if the wkhtmltopdf cache step already restored it.
    if [ ! -f "$wkhtmltox_deb" ]; then
        wget -O "$wkhtmltox_deb" https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
    fi
    sudo apt-get install -y "$wkhtmltox_deb"
}
if [ "${SKIP_WKHTMLTOX_SETUP:-0}" != "1" ]; then
    install_whktml &
    wkpid=$!
else
    wkpid=
fi

if ! restore_warm_bench; then
    bench init --skip-assets --frappe-path ~/frappe --python "$(which python)" frappe-bench

    cd ~/frappe-bench || exit

    sed -i 's/watch:/# watch:/g' Procfile
    sed -i 's/schedule:/# schedule:/g' Procfile
    sed -i 's/socketio:/# socketio:/g' Procfile
    sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

    CI=Yes bench build --app frappe
    save_warm_bench
fi

if [ -n "$wkpid" ]; then wait $wkpid; fi

mkdir -p ~/frappe-bench/sites/test_site

if [ "$DB" == "mariadb" ];then
    cp -r "${GITHUB_WORKSPACE}/.github/helper/site_config_mariadb.json" ~/frappe-bench/sites/test_site/site_config.json
    if [ "$db_host" != "127.0.0.1" ]; then
        sed -i "s/\"db_host\": \"127.0.0.1\"/\"db_host\": \"${db_host}\"/" ~/frappe-bench/sites/test_site/site_config.json
    fi
else
    cp -r "${GITHUB_WORKSPACE}/.github/helper/site_config_postgres.json" ~/frappe-bench/sites/test_site/site_config.json
fi


if [ "$DB" == "mariadb" ];then
    for _ in {1..60}; do
        if mariadb-admin ping --host "$db_host" --port 3306 -u root -proot --silent; then
            break
        fi
        sleep 1
    done
    mariadb-admin ping --host "$db_host" --port 3306 -u root -proot --silent

    mariadb --host "$db_host" --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'"
    mariadb --host "$db_host" --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

    # Throwaway-DB durability tuning at runtime. (innodb_doublewrite is read-only on MariaDB
    # 10.6, so it can't be disabled here — would need a server startup flag.)
    mariadb --host "$db_host" --port 3306 -u root -proot \
        -e "SET GLOBAL innodb_flush_log_at_trx_commit=0; SET GLOBAL sync_binlog=0;"

    # Opt-in DDL speedup: a shared tablespace avoids a create+fsync per DocType table during
    # reinstall — a big win under disk contention. But ROW_FORMAT=DYNAMIC must be accepted in
    # the system tablespace on this MariaDB. Enable with CI_INNODB_SHARED_TABLESPACE=1; if
    # reinstall then errors on table creation, unset it (off by default — zero risk).
    if [ "${CI_INNODB_SHARED_TABLESPACE:-0}" = "1" ]; then
        mariadb --host "$db_host" --port 3306 -u root -proot -e "SET GLOBAL innodb_file_per_table=0;"
    fi

    mariadb --host "$db_host" --port 3306 -u root -proot -e "CREATE USER 'test_frappe'@'${db_user_host}' IDENTIFIED BY 'test_frappe'"
    mariadb --host "$db_host" --port 3306 -u root -proot -e "CREATE DATABASE test_frappe"
    mariadb --host "$db_host" --port 3306 -u root -proot -e "GRANT ALL PRIVILEGES ON \`test_frappe\`.* TO 'test_frappe'@'${db_user_host}'"

    mariadb --host "$db_host" --port 3306 -u root -proot -e "FLUSH PRIVILEGES"
fi

if [ "$DB" == "postgres" ];then
    echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE DATABASE test_frappe" -U postgres;
    echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE USER test_frappe WITH PASSWORD 'test_frappe'" -U postgres;

    # Durability-off for speed (no fsync/synchronous_commit/full_page_writes) is applied by
    # start-db.sh's postgres `-o` flags on every start — setup job AND each test shard — so it is
    # NOT repeated here. The postgres workflow runs in-runner via start-db.sh, not a service
    # container.
fi

cd ~/frappe-bench || exit

run_ci_step "Get payments app" bench get-app payments --branch develop

# Opt-in: skip building erpnext's frontend assets. Server tests don't need them, but PDF
# tests (print formats) do — they pass only if the PDF renderer ignores missing assets.
# Enable with CI_SKIP_ERPNEXT_ASSETS=1 to test; if PDF tests fail, unset it.
erpnext_get_app_args=()
if [ "${CI_SKIP_ERPNEXT_ASSETS:-0}" = "1" ]; then erpnext_get_app_args=(--skip-assets); fi
run_ci_step "Get erpnext app" bench get-app erpnext "${GITHUB_WORKSPACE}" "${erpnext_get_app_args[@]}"

if [ "$TYPE" == "server" ]; then run_ci_step "Setup dev requirements" bench setup requirements --dev; fi

bench start >> ~/frappe-bench/bench_start.log 2>&1 &

# Under heavy concurrency, gunicorn's startup can delay redis coming up. reinstall and the
# tests need redis, so wait for it (best-effort, bounded) instead of racing — contention
# then slows the job rather than failing it.
wait_for_redis() {
    local cfg=~/frappe-bench/sites/common_site_config.json
    [ -f "$cfg" ] || return 0
    local ports port
    ports=$(python - "$cfg" <<'PY'
import json, re, sys
try:
    cfg = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for key in ("redis_cache", "redis_queue"):
    match = re.search(r":(\d+)", str(cfg.get(key, "")))
    if match:
        print(match.group(1))
PY
)
    for port in $ports; do
        local up=0
        for _ in $(seq 1 120); do
            if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
                exec 3>&- 3<&-; up=1
                break
            fi
            sleep 1
        done
        # Fail clearly instead of letting reinstall die later on a vague socket-connection error
        # when redis never bound.
        [ "$up" = "1" ] || { echo "redis did not come up on port $port"; return 1; }
    done
}
wait_for_redis

# Site setup: build the schema (~1000 DocTypes) into the DB. This is the single-threaded-Python
# bottleneck, but the fan-out amortises it — it runs once here in the setup job, and the test
# shards start the DB on the baked datadir instead of repeating the reinstall.
run_ci_step "Reinstall test site" bench --site test_site reinstall --yes
