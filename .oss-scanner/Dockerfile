# ERPNext for OSS Scanner. Enrolled at https://github.com/anthropics/oss-scanner/tree/main/projects/erpnext;
# the scanner builds this file with the repository as its context, and reads threat_model.md in this directory.
# Adapted from frappe_docker (images/production/Containerfile), but built from the scanner's checkout instead of a
# GitHub clone: the checkout is apps/erpnext in a bench on Frappe's develop branch, and /src is a symlink to it.
# MariaDB and Redis run inside this one container (the scanner has no compose services); start them with
# `frappe-services start`. A site, test_site, with ERPNext installed and its setup wizard completed is created
# during the build.
FROM python:3.14-slim-trixie

ARG NODE_VERSION=24
ARG FRAPPE_BRANCH=develop
ARG WKHTMLTOPDF_VERSION=0.12.6.1-3
ARG WKHTMLTOPDF_DISTRO=bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    NVM_DIR=/opt/nvm \
    NVM_SYMLINK_CURRENT=true \
    PATH=/opt/nvm/current/bin:/home/frappe/.local/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl wget git sudo procps file media-types tzdata-legacy cron less jq \
      build-essential pkg-config \
      # database and cache
      mariadb-server mariadb-client libmariadb-dev redis-server \
      # python package build dependencies
      libffi-dev liblcms2-dev libldap2-dev libsasl2-dev libtiff-dev libwebp-dev libbz2-dev libpq-dev \
      # PDF rendering: Chromium (as frappe_docker installs it), weasyprint and wkhtmltopdf
      chromium-headless-shell libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libpangocairo-1.0-0 fonts-cantarell xfonts-75dpi xfonts-base \
    && arch="$(dpkg --print-architecture)" \
    && deb="wkhtmltox_${WKHTMLTOPDF_VERSION}.${WKHTMLTOPDF_DISTRO}_${arch}.deb" \
    && curl -fsSLO "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/${deb}" \
    && apt-get install -y --no-install-recommends "./${deb}" && rm "${deb}" \
    && rm -rf /var/lib/apt/lists/*

# Frappe needs utf8mb4 with this exact collation, or bench new-site refuses the server.
RUN printf '[mysqld]\ncharacter-set-client-handshake = FALSE\ncharacter-set-server = utf8mb4\ncollation-server = utf8mb4_unicode_ci\nbind-address = 127.0.0.1\n\n[mysql]\ndefault-character-set = utf8mb4\n' \
      > /etc/mysql/mariadb.conf.d/99-frappe.cnf

# Node and yarn, through nvm as frappe_docker does, somewhere both root and frappe can use them.
RUN mkdir -p "${NVM_DIR}" \
    && curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.6/install.sh | bash \
    && . "${NVM_DIR}/nvm.sh" \
    && nvm install "${NODE_VERSION}" && nvm alias default "${NODE_VERSION}" \
    && npm install -g yarn \
    && rm -rf "${NVM_DIR}/.cache" \
    && node --version && yarn --version

# The checkout belongs to frappe, but the scanner works in /src as root: let git read it anyway.
RUN useradd -m -s /bin/bash frappe \
    && echo "frappe ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/frappe \
    && git config --system --add safe.directory '*' \
    && pip install --no-cache-dir frappe-bench

# Starts and stops MariaDB and the two Redis servers the bench is configured for. Works offline.
RUN cat > /usr/local/bin/frappe-services <<'EOF' && chmod 755 /usr/local/bin/frappe-services
#!/bin/sh
set -e
case "${1:-start}" in
  start)
    mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld
    if ! mariadb-admin -uroot -proot ping --silent 2>/dev/null; then
      (mariadbd-safe --user=mysql >/dev/null 2>&1 &)
      for _ in $(seq 60); do mariadb-admin ping --silent 2>/dev/null && break; sleep 1; done
    fi
    for port in 13000 11000; do
      redis-cli -p "$port" ping >/dev/null 2>&1 || redis-server --port "$port" --bind 127.0.0.1 --save '' --daemonize yes
    done ;;
  stop)
    mariadb-admin -uroot -proot shutdown 2>/dev/null || mariadb-admin shutdown || true
    for port in 13000 11000; do redis-cli -p "$port" shutdown nosave 2>/dev/null || true; done ;;
esac
EOF

# scanner contract: the checkout lives inside the image, at /src
COPY --chown=frappe:frappe . /src
WORKDIR /src

# Build a bench on Frappe develop (ERPNext develop needs frappe >=17.0.0-dev), then move the checkout in as the erpnext
# app and point /src back at it. The app must be a real directory inside the bench so paths resolve inside it.
USER frappe
RUN cd /home/frappe \
    && bench init --skip-assets --frappe-branch "${FRAPPE_BRANCH}" --python "$(command -v python3)" frappe-bench \
    && cd frappe-bench \
    && sudo mv /src apps/erpnext && sudo ln -s /home/frappe/frappe-bench/apps/erpnext /src \
    && echo erpnext >> sites/apps.txt \
    && env/bin/pip install --no-cache-dir -e apps/erpnext \
    && bench setup requirements && bench setup requirements --dev \
    && bench build \
    && bench set-config -g chromium_path /usr/lib/chromium/chromium-headless-shell

# Create test_site with ERPNext installed (Administrator password: admin; MariaDB root password: root). Administrator
# completes the setup wizard (company "Scanner Company", abbreviation SC, country India), because permission testing
# on a site without it gives misleading results. ERPNext's test suite cannot run on such a site (it creates its own
# companies and fiscal years), so tests are not enabled. One user per actor level, all with the password
# scanner-user-pw:
#   website@example.com        Website User (customer/supplier portal)
#   user@example.com           plain System User (only the Desk User role)
#   accounts-user@example.com  Accounts User
#   sales-user@example.com     Sales User
#   stock-user@example.com     Stock User
#   manager@example.com        System Manager, for the "they can already do this" test
USER root
RUN set -e \
    && mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld \
    && (mariadbd-safe --user=mysql >/dev/null 2>&1 &) \
    && for _ in $(seq 60); do mariadb-admin ping --silent 2>/dev/null && break; sleep 1; done \
    && mariadb -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'root'; FLUSH PRIVILEGES;" \
    && frappe-services start \
    && su frappe -c "cd /home/frappe/frappe-bench \
         && bench new-site test_site --db-root-password root --admin-password admin --mariadb-user-host-login-scope=localhost --install-app erpnext \
         && bench --site test_site set-config host_name http://test_site:8000 \
         && bench --site test_site execute frappe.desk.page.setup_wizard.setup_wizard.setup_complete --kwargs \"{'args': {'language': 'English', 'country': 'India', 'timezone': 'Asia/Kolkata', 'currency': 'INR', 'company_name': 'Scanner Company', 'company_abbr': 'SC', 'chart_of_accounts': 'Standard', 'fy_start_date': '2026-04-01', 'fy_end_date': '2027-03-31'}}\" \
         && bench --site test_site execute frappe.is_setup_complete | grep -qix true \
         && bench --site test_site add-user website@example.com --first-name Website --password scanner-user-pw --user-type 'Website User' \
         && bench --site test_site add-user user@example.com --first-name Plain --password scanner-user-pw --user-type 'System User' --add-role 'Desk User' \
         && bench --site test_site add-user accounts-user@example.com --first-name Accounts --password scanner-user-pw --user-type 'System User' --add-role 'Accounts User' \
         && bench --site test_site add-user sales-user@example.com --first-name Sales --password scanner-user-pw --user-type 'System User' --add-role 'Sales User' \
         && bench --site test_site add-user stock-user@example.com --first-name Stock --password scanner-user-pw --user-type 'System User' --add-role 'Stock User' \
         && bench --site test_site add-user manager@example.com --first-name Manager --password scanner-user-pw --user-type 'System User' --add-role 'System Manager' \
         && bench use test_site" \
    && frappe-services stop

# Cheap check that the image works: the site answers over HTTP with ERPNext installed. A failure does not abort the
# build.
RUN frappe-services start \
    && (su frappe -c "cd /home/frappe/frappe-bench && bench --site test_site list-apps | grep -q erpnext \
          && (bench serve --port 8000 > /tmp/serve.log 2>&1 &) \
          && for _ in \$(seq 60); do curl -sf -H 'Host: test_site' http://127.0.0.1:8000/api/method/ping && break; sleep 1; done \
          && curl -sf -H 'Host: test_site' http://127.0.0.1:8000/api/method/ping" \
        || echo "WARNING: erpnext smoke check failed") \
    ; pkill -f 'bench serve' ; pkill -f 'frappe.utils.bench_helper' ; frappe-services stop
