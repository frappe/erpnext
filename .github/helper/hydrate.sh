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
        "ERPNEXT_CI_USER='$ci_user' DB_HOST='$db_host' bash '$0'"
fi

cd ~/frappe-bench

# Start the DB on the datadir baked into the artifact. It's already populated (the setup job
# reinstalled into this very datadir), so there is NO restore — the server comes up on the
# existing files. This is what replaces the per-shard SQL replay.
bash ~/frappe-bench/start-db.sh

bench start >> ~/frappe-bench/bench_start.log 2>&1 &

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
