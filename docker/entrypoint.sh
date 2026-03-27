#!/bin/bash
# Container entrypoint for the ERPNext fork image.
# The CMD (passed as $1) selects the service role.
set -euo pipefail

BENCH_DIR=/home/frappe/frappe-bench
SITE_NAME="${SITE_NAME:-erpnext.localhost}"

# ── Helpers ───────────────────────────────────────────────────────────────────

wait_for_db() {
    local host="${DB_HOST:-db}"
    local port="${DB_PORT:-3306}"
    local user="${DB_ROOT_USER:-root}"
    local pass="${DB_ROOT_PASSWORD:-admin}"
    echo "Waiting for MariaDB at ${host}:${port} ..."
    until mariadb-admin ping -h"${host}" -P"${port}" -u"${user}" -p"${pass}" --silent 2>/dev/null; do
        sleep 2
    done
    echo "MariaDB is ready."
}

wait_for_redis() {
    local addr="${1:-redis-cache:6379}"
    local host="${addr%%:*}"
    local port="${addr##*:}"
    echo "Waiting for Redis at ${host}:${port} ..."
    # Use Python (always available) instead of nc to avoid extra package deps
    until python3 -c "import socket; socket.create_connection(('${host}', ${port}), 2)" 2>/dev/null; do
        sleep 2
    done
    echo "Redis ${host} is ready."
}

# ── Service roles ─────────────────────────────────────────────────────────────

case "${1:-web}" in

  # ── configurator: write common_site_config.json ──────────────────────────
  configurator)
    wait_for_db
    wait_for_redis "${REDIS_CACHE:-redis-cache:6379}"
    wait_for_redis "${REDIS_QUEUE:-redis-queue:6379}"
    wait_for_redis "${REDIS_SOCKETIO:-redis-socketio:6379}"

    cd "${BENCH_DIR}"
    bench set-config -g db_host       "${DB_HOST:-db}"
    bench set-config -g db_port       "${DB_PORT:-3306}"
    bench set-config -g redis_cache   "redis://${REDIS_CACHE:-redis-cache:6379}"
    bench set-config -g redis_queue   "redis://${REDIS_QUEUE:-redis-queue:6379}"
    bench set-config -g redis_socketio "redis://${REDIS_SOCKETIO:-redis-socketio:6379}"
    bench set-config -g socketio_port 9000
    echo "✓ common_site_config.json written."
    ;;

  # ── create-site: initialise the Frappe site ───────────────────────────────
  create-site)
    cd "${BENCH_DIR}"
    if [ -f "sites/${SITE_NAME}/site_config.json" ]; then
        echo "Site '${SITE_NAME}' already exists – skipping creation."
    else
        echo "Creating site '${SITE_NAME}' ..."
        bench new-site \
            --no-mariadb-socket \
            --db-root-username  "${DB_ROOT_USER:-root}" \
            --db-root-password  "${DB_ROOT_PASSWORD:-admin}" \
            --admin-password    "${ADMIN_PASSWORD:-admin}" \
            --install-app payments \
            --install-app erpnext \
            "${SITE_NAME}"
        bench --site "${SITE_NAME}" set-config host_name "http://${SITE_NAME}"
        echo "✓ Site '${SITE_NAME}' created."
    fi
    ;;

  # ── web: Gunicorn WSGI server ─────────────────────────────────────────────
  web)
    cd "${BENCH_DIR}"
    exec gunicorn \
        --bind     0.0.0.0:8000 \
        --workers  "${GUNICORN_WORKERS:-2}" \
        --worker-class gevent \
        --worker-connections 1000 \
        --timeout  120 \
        --preload \
        frappe.app:application
    ;;

  # ── socketio: real-time / WebSocket server ────────────────────────────────
  socketio)
    exec node "${BENCH_DIR}/apps/frappe/socketio.js"
    ;;

  # ── scheduler: Frappe background scheduler ───────────────────────────────
  scheduler)
    cd "${BENCH_DIR}"
    exec bench schedule
    ;;

  # ── worker: Celery/RQ worker (WORKER_TYPE controls queue) ────────────────
  worker)
    cd "${BENCH_DIR}"
    exec bench worker --queue "${WORKER_TYPE:-short,default,long}"
    ;;

  # ── pass-through for any other command ───────────────────────────────────
  *)
    exec "$@"
    ;;

esac
