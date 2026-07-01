#!/bin/bash
#
# Hydrate a test shard from the setup job's artifact.
#
# The bench (apps, venv, node_modules, sites) is already on disk at ~/frappe-bench — the
# workflow untar'd it from the artifact the setup job built. So there is NO bench init, no
# asset build, and no reinstall here: just bring the DB up on the baked datadir and start redis
# so tests can run. The whole point is that the expensive work happened ONCE in the setup job.
#
set -e

ci_user="${ERPNEXT_CI_USER:-frappe}"
db_host="${DB_HOST:-127.0.0.1}"

# Re-exec as the ci user (uid 1001) so bench/cache ownership matches the artifact, same as
# install.sh. The workflow untar'd as root with -p, so the files are already owned by ci.
if [ "$(id -u)" = "0" ] && [ "${SKIP_SYSTEM_SETUP:-0}" = "1" ] && [ "$ci_user" != "root" ]; then
    exec su -m "$ci_user" -s /bin/bash -c \
        "ERPNEXT_CI_USER='$ci_user' DB_HOST='$db_host' DB='${DB:-}' bash '$0'"
fi

cd ~/frappe-bench

# Start the DB on the datadir baked into the artifact. It's already populated (the setup job
# reinstalled into this very datadir), so there is NO restore — the server comes up on the
# existing files. This is what replaces the per-shard SQL replay.
bash ~/frappe-bench/start-db.sh

# Bring up redis (lightmode unit tests need cache + queue). In the self-hosted container we use the
# full `bench start` (web/workers too, like install.sh). On the bare GitHub Postgres shard
# `bench start` (honcho) lagged — it blocks the redis procs behind web/worker procs the lightmode
# suite never uses, so the wait below burned its full timeout (~4m). There, start the two redis
# instances directly: fast and deterministic.
if [ "${DB:-mariadb}" = "postgres" ]; then
    # Start redis directly as daemons — reliable and persists across steps. Do NOT route it through
    # `bench start`: honcho tears the whole process group down if any one Procfile proc dies on the
    # bare shard, which took redis with it (redis @ 13000 refused in Run Tests). Keeping redis
    # independent is what makes it survive. The web server (for PDF tests) is NOT started here — a
    # backgrounded server doesn't survive into the next step; it's started inside the Run Tests step.
    for conf in redis_cache redis_queue; do
        [ -f ~/frappe-bench/config/$conf.conf ] && redis-server ~/frappe-bench/config/$conf.conf --daemonize yes
    done
else
    bench start >> ~/frappe-bench/bench_start.log 2>&1 &
fi

# Wait for redis, failing fast instead of silently burning minutes if it never comes up.
cfg=~/frappe-bench/sites/common_site_config.json
if [ -f "$cfg" ]; then
    ports=$(python - "$cfg" <<'PY'
import json, re, sys
try:
    cfg = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for key in ("redis_cache", "redis_queue"):
    m = re.search(r":(\d+)", str(cfg.get(key, "")))
    if m:
        print(m.group(1))
PY
)
    for port in $ports; do
        up=0
        for _ in $(seq 1 60); do
            if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then exec 3>&- 3<&-; up=1; break; fi
            sleep 1
        done
        [ "$up" = "1" ] || { echo "redis did not come up on port $port"; exit 1; }
    done
fi

echo "Hydrated: DB up on baked datadir, redis up — ready for tests."
