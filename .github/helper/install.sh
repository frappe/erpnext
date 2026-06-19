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

wait $apt_pid
wait $pip_pid
wait $clone_pid

pushd frappe
git checkout FETCH_HEAD
popd

# ---------------------------------------------------------------------------
# Phase 2 — bench init and site setup
# ---------------------------------------------------------------------------

# Setup 2 sites

bench init --skip-assets --frappe-path ~/frappe --python "$(which python)" frappe-bench

function setup_site() {
    local site=$1

    mkdir ~/frappe-bench/sites/$site

    if [ "$DB" == "mariadb" ];then
	sed "s/test_frappe/${site}/g" "${GITHUB_WORKSPACE}/.github/helper/site_config_mariadb.json" > ~/frappe-bench/sites/$site/site_config.json
    else
	sed "s/test_frappe/${site}/g" "${GITHUB_WORKSPACE}/.github/helper/site_config_postgres.json" > ~/frappe-bench/sites/$site/site_config.json
    fi

    if [ "$DB" == "mariadb" ];then
	mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'"
	mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

	# Belt-and-suspenders: also set performance variables at runtime in case
	# MARIADB_EXTRA_FLAGS was not honoured by the container image.
	mariadb --host 127.0.0.1 --port 3306 -u root -proot \
		-e "SET GLOBAL innodb_flush_log_at_trx_commit=0; SET GLOBAL sync_binlog=0;"

	mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE USER '$site'@'localhost' IDENTIFIED BY '$site'"
	mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE DATABASE $site"
	mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "GRANT ALL PRIVILEGES ON \`$site\`.* TO '$site'@'localhost'"

	mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "FLUSH PRIVILEGES"
    fi

    if [ "$DB" == "postgres" ];then
	echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE DATABASE $site" -U postgres;
	echo "travis" | psql -h 127.0.0.1 -p 5432 -c "CREATE USER $site WITH PASSWORD '$site'" -U postgres;
    fi
}

# Site names are driven by the matrix via SITE1 / SITE2 env vars set in the workflow.
declare -a sites
sites=("$SITE1" "$SITE2")

for site in "${sites[@]}"; do
    setup_site "$site"
done

install_whktml() {
    # Re-use the .deb if the wkhtmltopdf cache step already restored it.
    if [ ! -f /tmp/wkhtmltox.deb ]; then
        wget -O /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
    fi
    sudo apt install /tmp/wkhtmltox.deb
}
install_whktml &
wkpid=$!


cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

bench get-app payments --branch develop
bench get-app erpnext "${GITHUB_WORKSPACE}"

if [ "$TYPE" == "server" ]; then bench setup requirements --dev; fi

wait $wkpid

bench start &>> ~/frappe-bench/bench_start.log &
CI=Yes bench build --app frappe &
reinstall_pids=()
for site in "${sites[@]}"; do
    bench --site "$site" reinstall --yes &
    reinstall_pids+=($!)
done
for pid in "${reinstall_pids[@]}"; do
    wait "$pid"
done
