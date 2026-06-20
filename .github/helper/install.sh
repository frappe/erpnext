#!/bin/bash

set -e

cd ~ || exit

githubbranch=${GITHUB_BASE_REF:-${GITHUB_REF##*/}}
frappeuser=${FRAPPE_USER:-"frappe"}
frappecommitish=${FRAPPE_BRANCH:-$githubbranch}

# ---------------------------------------------------------------------------
# Phase 1 — parallelise the three slow, independent setup steps:
#   a) system packages   b) frappe-bench pip install   c) frappe git fetch
# ---------------------------------------------------------------------------

sudo apt update

# apt remove/install must run sequentially but can overlap with pip and git.
sudo apt remove mysql-server mysql-client
sudo apt install libcups2-dev redis-server mariadb-client libmariadb-dev &
apt_pid=$!

pip install frappe-bench &
pip_pid=$!

mkdir frappe
(
  cd frappe
  git init
  git remote add origin "https://github.com/${frappeuser}/frappe"
  git fetch origin "${frappecommitish}" --depth 1
) &
clone_pid=$!

install_whktml() {
    # Re-use the .deb if the wkhtmltopdf cache step already restored it.
    if [ ! -f /tmp/wkhtmltox.deb ]; then
        wget -O /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
    fi
    sudo apt install /tmp/wkhtmltox.deb
}
install_whktml &
wkpid=$!


wait $wkpid
wait $apt_pid
wait $pip_pid
wait $clone_pid

# Reset mariadb root password
sudo mariadb -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('test_pass'); FLUSH PRIVILEGES;"

pushd frappe
git checkout FETCH_HEAD
popd

# ---------------------------------------------------------------------------
# Phase 2 — bench init and site setup
# ---------------------------------------------------------------------------

bench init --skip-assets --frappe-path ~/frappe --python "$(which python)" frappe-bench

cd frappe-bench
bench get-app erpnext "${GITHUB_WORKSPACE}" --skip-assets
bench get-app payments --branch develop --skip-assets
bench setup requirements --dev

function setup_site() {
    local site=$1
    bench new-site --db-root-username root --db-root-password test_pass --admin-password test_pass $site --install-app erpnext --install-app payments &
    new_site_pids+=($!)
}

# Site names are driven by the matrix via SITE1 / SITE2 env vars set in the workflow.
declare -a sites
sites=("$SITE1" "$SITE2")

for site in "${sites[@]}"; do
    setup_site "$site"
done

for pid in "${new_site_pids[@]}"; do
    wait "$pid"
done

# disable unwated redis, socketio and watcher processes
sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile
