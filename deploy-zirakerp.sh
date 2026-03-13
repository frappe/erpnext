#!/bin/bash
##############################################################################
# ZirakERP Deployment Script for Hostinger VPS (Ubuntu 24.04)
# Server: srv928799.hstgr.cloud (148.230.104.240)
# VPS: KVM 1 — 1 CPU, 4 GB RAM, 50 GB Disk
#
# Usage:
#   export MARIADB_ROOT_PASS="your_secure_password"
#   export ADMIN_PASS="your_admin_password"
#   sudo bash deploy-zirakerp.sh
#
# This script will:
# 1. Stop and remove n8n (Docker containers)
# 2. Create swap (critical for 4GB RAM)
# 3. Install all dependencies for Frappe/ERPNext
# 4. Set up frappe-bench with ZirakERP
# 5. Configure production (Nginx, Supervisor, SSL-ready)
##############################################################################

set -euo pipefail

# ========================
# CONFIGURATION
# ========================
FRAPPE_USER="frappe"
BENCH_DIR="/home/${FRAPPE_USER}/frappe-bench"
SITE_NAME="srv928799.hstgr.cloud"
ZIRAKERP_REPO="https://github.com/alanasm1958/ZirakERP.git"
ZIRAKERP_BRANCH="develop"
FRAPPE_BRANCH="version-15"
NODE_VERSION="18"

# Read passwords from environment or prompt
if [ -z "${MARIADB_ROOT_PASS:-}" ]; then
    read -sp "Enter MariaDB root password: " MARIADB_ROOT_PASS
    echo
fi
if [ -z "${ADMIN_PASS:-}" ]; then
    read -sp "Enter ZirakERP admin password: " ADMIN_PASS
    echo
fi

if [ ${#MARIADB_ROOT_PASS} -lt 8 ] || [ ${#ADMIN_PASS} -lt 8 ]; then
    echo "ERROR: Passwords must be at least 8 characters."
    exit 1
fi

# Must run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root (sudo)."
    exit 1
fi

echo "=============================================="
echo "  ZirakERP Deployment Starting..."
echo "=============================================="

# ========================
# STEP 1: Stop & Remove n8n
# ========================
echo ""
echo "[1/9] Stopping and removing n8n..."
if command -v docker &>/dev/null; then
    docker stop $(docker ps -aq) 2>/dev/null || true
    docker rm $(docker ps -aq) 2>/dev/null || true
    docker system prune -af --volumes 2>/dev/null || true
    echo "  Done — n8n removed and Docker cleaned up"
else
    echo "  Skipped — Docker not installed"
fi

# ========================
# STEP 2: Setup Swap (before heavy installs)
# ========================
echo ""
echo "[2/9] Setting up swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "  Done — 2GB swap created"
else
    echo "  Skipped — swap already exists"
fi

# ========================
# STEP 3: System Update & Dependencies
# ========================
echo ""
echo "[3/9] Updating system and installing dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y \
    git \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-setuptools \
    software-properties-common \
    build-essential \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    xvfb \
    libfontconfig \
    wkhtmltopdf \
    curl \
    wget \
    sudo \
    cron \
    nginx \
    supervisor \
    redis-server \
    fail2ban

echo "  Done — system dependencies installed"

# ========================
# STEP 4: Install Node.js 18
# ========================
echo ""
echo "[4/9] Installing Node.js ${NODE_VERSION}..."
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
apt-get install -y nodejs
npm install -g yarn
echo "  Node: $(node -v), npm: $(npm -v), yarn: $(yarn -v)"
echo "  Done — Node.js installed"

# ========================
# STEP 5: Install & Configure MariaDB
# ========================
echo ""
echo "[5/9] Installing MariaDB..."
apt-get install -y mariadb-server mariadb-client libmariadb-dev

# Configure MariaDB for Frappe (tuned for 4GB RAM)
cat > /etc/mysql/mariadb.conf.d/99-frappe.cnf << 'MARIADBCONF'
[mysqld]
innodb-file-format=barracuda
innodb-file-per-table=1
innodb-large-prefix=1
character-set-client-handshake=FALSE
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
innodb_buffer_pool_size=512M
innodb_log_file_size=128M
innodb_log_buffer_size=32M
innodb_flush_log_at_trx_commit=2
max_allowed_packet=256M

[mysql]
default-character-set=utf8mb4
MARIADBCONF

systemctl restart mariadb
systemctl enable mariadb

# Secure MariaDB
mysql -u root <<MYSQL_SECURE
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MARIADB_ROOT_PASS}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
MYSQL_SECURE

echo "  Done — MariaDB installed and configured"

# ========================
# STEP 6: Configure Redis
# ========================
echo ""
echo "[6/9] Configuring Redis..."
systemctl enable redis-server
systemctl start redis-server
echo "  Done — Redis configured"

# ========================
# STEP 7: Create frappe user & install bench
# ========================
echo ""
echo "[7/9] Creating frappe user and installing bench..."

# Create frappe user if not exists
id -u ${FRAPPE_USER} &>/dev/null || useradd -m -s /bin/bash ${FRAPPE_USER}
usermod -aG sudo ${FRAPPE_USER}
echo "${FRAPPE_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${FRAPPE_USER}

# Ensure ~/.local/bin is in PATH for frappe user
su - ${FRAPPE_USER} -c 'grep -q "\.local/bin" ~/.bashrc 2>/dev/null || echo "export PATH=\$HOME/.local/bin:\$PATH" >> ~/.bashrc'
su - ${FRAPPE_USER} -c 'grep -q "\.local/bin" ~/.profile 2>/dev/null || echo "export PATH=\$HOME/.local/bin:\$PATH" >> ~/.profile'

# Install bench as frappe user
su - ${FRAPPE_USER} << 'BENCHINSTALL'
set -e
export PATH=$HOME/.local/bin:$PATH

pip3 install frappe-bench --break-system-packages 2>/dev/null || pip3 install frappe-bench

# Verify bench is accessible
which bench
bench --version

# Initialize bench (remove previous incomplete attempt if exists)
cd /home/frappe
if [ -d "frappe-bench" ]; then
    echo "  Removing previous incomplete frappe-bench..."
    rm -rf frappe-bench
fi

bench init frappe-bench --frappe-branch version-15 --python python3
cd frappe-bench

# Set bench to production mode config
bench set-config -g developer_mode 0
bench set-config -g gunicorn_workers 3
bench set-config -g server_script_enabled 1
BENCHINSTALL

echo "  Done — Frappe bench initialized"

# ========================
# STEP 8: Install ZirakERP & Create Site
# ========================
echo ""
echo "[8/9] Installing ZirakERP and creating site..."
su - ${FRAPPE_USER} << ERPINSTALL
set -e
export PATH=\$HOME/.local/bin:\$PATH
cd /home/frappe/frappe-bench

# Get ZirakERP app
bench get-app ${ZIRAKERP_REPO} --branch ${ZIRAKERP_BRANCH}

# Create new site
bench new-site ${SITE_NAME} \
    --mariadb-root-password '${MARIADB_ROOT_PASS}' \
    --admin-password '${ADMIN_PASS}' \
    --install-app erpnext

# Set as default site
bench use ${SITE_NAME}

# Build assets
bench build
ERPINSTALL

echo "  Done — ZirakERP installed and site created"

# ========================
# STEP 9: Setup Production (Nginx + Supervisor)
# ========================
echo ""
echo "[9/9] Setting up production..."

# Stop default nginx to avoid conflicts
systemctl stop nginx 2>/dev/null || true

su - ${FRAPPE_USER} << 'PRODSETUP'
set -e
export PATH=$HOME/.local/bin:$PATH
cd /home/frappe/frappe-bench
sudo bench setup production frappe --yes
PRODSETUP

# Enable and start services
systemctl enable supervisor
systemctl enable nginx
systemctl restart supervisor
systemctl restart nginx

# Restrict frappe user sudo to only required commands
cat > /etc/sudoers.d/${FRAPPE_USER} << SUDOERS
${FRAPPE_USER} ALL=(ALL) NOPASSWD: /usr/bin/supervisorctl *, /usr/bin/systemctl restart nginx, /usr/bin/systemctl reload nginx, /usr/bin/systemctl restart supervisor, /usr/bin/systemctl reload supervisor, /usr/sbin/nginx -t
SUDOERS
chmod 440 /etc/sudoers.d/${FRAPPE_USER}
echo "  Restricted frappe sudo to supervisor/nginx commands only"

# ========================
# STEP 10: Setup SSL (optional, non-blocking)
# ========================
echo ""
echo "[10/10] Attempting SSL setup..."
su - ${FRAPPE_USER} -c "cd ${BENCH_DIR} && bench setup lets-encrypt ${SITE_NAME} --non-interactive" 2>/dev/null || echo "  SSL setup skipped — configure manually after DNS is pointed to this server"

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Configure fail2ban
systemctl enable fail2ban
systemctl start fail2ban

echo ""
echo "=============================================="
echo "  ZirakERP Deployment Complete!"
echo "=============================================="
echo ""
echo "  Access your site at:"
echo "    http://${SITE_NAME}"
echo "    http://148.230.104.240"
echo ""
echo "  Login:"
echo "    User: Administrator"
echo "    Password: (the admin password you entered)"
echo ""
echo "  Next steps:"
echo "    1. Change passwords after first login"
echo "    2. Setup SSL:"
echo "       sudo -H bench setup lets-encrypt ${SITE_NAME}"
echo "    3. Setup backups:"
echo "       bench --site ${SITE_NAME} backup"
echo ""
echo "=============================================="
