#!/bin/bash
#
# Run MariaDB INSIDE the runner container, on a datadir we control. Because the datadir can be
# packaged into the bench artifact, test shards start an already-loaded server instead of
# replaying a SQL dump (the ~60s hydrate restore). Each shard gets its own copy → isolation kept.
#
# CI_DB_DATADIR picks the path:
#   - setup job:  /home/ci/db-data  (OUTSIDE the bench, so install.sh's `rm -rf ~/frappe-bench`
#                 doesn't wipe it; it's moved into the bench just before packaging)
#   - test shard: ~/frappe-bench/mariadb-data  (where the artifact untar'd it)
#
# Idempotent: inits a fresh datadir if absent (setup), else starts on the existing one (shards).
#
set -e

ci_user="${ERPNEXT_CI_USER:-frappe}"

# Re-exec as the ci user so mariadbd and the datadir are owned consistently (root mariadbd is
# refused anyway). Mirrors install.sh's user switch.
if [ "$(id -u)" = "0" ] && [ "${SKIP_SYSTEM_SETUP:-0}" = "1" ] && [ "$ci_user" != "root" ]; then
    exec su -m "$ci_user" -s /bin/bash -c \
        "ERPNEXT_CI_USER='$ci_user' CI_DB_DATADIR='${CI_DB_DATADIR:-}' DB='${DB:-}' bash '$0'"
fi

# --- PostgreSQL (GitHub-hosted CI): run in-runner on a PGDATA so it bakes into the artifact,
# same idea as the mariadb datadir. Trust auth (throwaway CI) skips password setup; durability
# off for speed. Postgres is preinstalled on ubuntu-latest under /usr/lib/postgresql/<ver>/bin.
if [ "${DB:-mariadb}" = "postgres" ]; then
    PG_BIN=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)
    [ -n "$PG_BIN" ] && export PATH="$PG_BIN:$PATH"
    PGDATA="${CI_DB_DATADIR:-$HOME/frappe-bench/pgdata}"
    if [ ! -d "$PGDATA/base" ]; then
        initdb -D "$PGDATA" -U postgres --auth-local=trust --auth-host=trust >/dev/null
        echo "host all all 127.0.0.1/32 trust" >> "$PGDATA/pg_hba.conf"
    fi
    pg_ctl -D "$PGDATA" -w -o "-p 5432 -c listen_addresses=127.0.0.1 -c unix_socket_directories=$PGDATA -c fsync=off -c synchronous_commit=off -c full_page_writes=off" start
    echo "PostgreSQL up in-runner (pgdata=$PGDATA)"
    exit 0
fi

# --- MariaDB ---
DATADIR="${CI_DB_DATADIR:-$HOME/frappe-bench/mariadb-data}"
SOCK="$DATADIR/mysqld.sock"
fresh=0

if [ ! -d "$DATADIR/mysql" ]; then
    mkdir -p "$DATADIR"
    mariadb-install-db --no-defaults --datadir="$DATADIR" \
        --auth-root-authentication-method=normal --skip-test-db >/dev/null 2>&1
    fresh=1
fi

# Throwaway-CI durability off; bind TCP 127.0.0.1:3306 so bench/install.sh connect as usual.
mariadbd --no-defaults --datadir="$DATADIR" --socket="$SOCK" --pid-file="$DATADIR/mysqld.pid" \
    --port=3306 --bind-address=127.0.0.1 \
    --innodb-flush-log-at-trx-commit=0 --sync-binlog=0 --skip-log-bin \
    > "$HOME/mariadb.log" 2>&1 &

up=0
for _ in $(seq 1 60); do
    if mariadb-admin --socket="$SOCK" ping --silent 2>/dev/null; then up=1; break; fi
    sleep 1
done
# Fail loudly instead of letting the loop fall through (exit 0 of the last `sleep`) into SQL that
# would error with a vague socket-connection failure.
[ "$up" = "1" ] || { echo "mariadbd did not come up on $SOCK"; cat "$HOME/mariadb.log" 2>/dev/null; exit 1; }

if [ "$fresh" = "1" ]; then
    # A fresh datadir has only a password-less root@localhost. Give it the password install.sh
    # uses, plus a TCP-reachable root@127.0.0.1, so the rest of install.sh works unchanged.
    mariadb --no-defaults --socket="$SOCK" -u root <<'SQL'
ALTER USER 'root'@'localhost' IDENTIFIED BY 'root';
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY 'root';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL
fi

echo "MariaDB up in-container (datadir=$DATADIR, fresh=$fresh)"
