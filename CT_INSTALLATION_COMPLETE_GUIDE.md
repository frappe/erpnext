# ERPNext v16 Complete Installation Guide for LXC/CT

**Last Updated:** December 18, 2025
**ERPNext Version:** 16.0.0-dev
**Tested On:** Ubuntu 22.04.5 LTS (LXC Container)
**Installation Time:** ~45-60 minutes

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Container Configuration](#container-configuration)
3. [Step-by-Step Installation](#step-by-step-installation)
4. [Troubleshooting](#troubleshooting)
5. [Post-Installation](#post-installation)
6. [Maintenance & Operations](#maintenance--operations)

---

## Prerequisites

### Recommended Container Specifications

- **OS:** Ubuntu 22.04 LTS (most compatible)
- **CPU:** 4 cores minimum
- **RAM:** 8GB recommended (4GB minimum)
- **Storage:** 50GB+ recommended
- **Network:** Public IP with ports 80, 443 accessible

### Container Features Required

For LXC/Proxmox containers:
```bash
features: nesting=1
```

---

## Container Configuration

### Create LXC Container (Proxmox Example)

```bash
pct create 100 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname erpnext \
  --memory 8192 \
  --swap 4096 \
  --cores 4 \
  --rootfs local-lvm:50 \
  --features nesting=1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1
```

---

## Step-by-Step Installation

### Step 1: System Verification

```bash
echo "=== OS Information ==="
cat /etc/os-release | grep -E "PRETTY_NAME|VERSION_ID"

echo ""
echo "=== System Resources ==="
echo "CPU Cores: $(nproc)"
echo "RAM Total: $(free -h | grep Mem | awk '{print $2}')"
echo "RAM Available: $(free -h | grep Mem | awk '{print $7}')"
echo "Disk Space: $(df -h / | tail -1 | awk '{print $2 " total, " $4 " available"}')"

echo ""
echo "=== Network Information ==="
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -I | awk '{print $1}')"

echo ""
echo "=== Internet Connectivity Test ==="
ping -c 2 8.8.8.8 > /dev/null 2>&1 && echo "✓ Internet: Connected" || echo "✗ Internet: No connection"
ping -c 2 google.com > /dev/null 2>&1 && echo "✓ DNS: Working" || echo "✗ DNS: Not working"
```

**Expected Results:**
- Ubuntu 22.04.5 LTS
- 4+ CPU cores
- 4.4GB+ RAM
- 400GB+ disk space
- Internet and DNS working

---

### Step 2: Update System & Install Dependencies

```bash
echo ">>> Updating package lists..."
apt-get update -qq

echo ">>> Upgrading existing packages..."
apt-get upgrade -y -qq

echo ">>> Installing essential build tools and libraries..."
apt-get install -y \
    git \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-venv \
    software-properties-common \
    libssl-dev \
    libffi-dev \
    libmysqlclient-dev \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff-dev \
    zlib1g-dev \
    curl \
    wget \
    vim \
    htop \
    supervisor \
    fontconfig \
    xfonts-75dpi \
    xfonts-base \
    libxrender1 \
    libxext6 \
    xfonts-encodings \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev \
    gir1.2-glib-2.0

echo ">>> Verifying installations..."
echo "Git: $(git --version)"
echo "Pip: $(pip3 --version | head -c 50)"
echo "Build tools: $(gcc --version | head -1)"
```

---

### Step 3: Install Python 3.11

```bash
echo ">>> Adding Python repository..."
add-apt-repository ppa:deadsnakes/ppa -y

echo ">>> Updating package lists..."
apt-get update -qq

echo ">>> Installing Python 3.11..."
apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3.11-distutils

echo ">>> Upgrading pip for Python 3.11..."
python3.11 -m pip install --upgrade pip setuptools wheel

echo ">>> Setting Python 3.11 as default..."
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 2
update-alternatives --set python3 /usr/bin/python3.11

echo ">>> Current default Python:"
python3 --version
```

**Expected Output:** `Python 3.11.14`

---

### Step 4: Install & Configure MariaDB

```bash
echo ">>> Installing MariaDB Server..."
apt-get install -y mariadb-server mariadb-client

echo ">>> Starting MariaDB service..."
systemctl start mariadb
systemctl enable mariadb

echo ">>> Configuring MariaDB for ERPNext..."
cat > /etc/mysql/mariadb.conf.d/erpnext.cnf << 'EOF'
[mysqld]
# ERPNext Configuration
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# InnoDB Settings
innodb_buffer_pool_size = 1G
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 1
innodb_file_per_table = 1

# Binary Logging
binlog_format = row
log_bin = /var/log/mysql/mysql-bin.log
max_binlog_size = 100M
expire_logs_days = 7

# Connection Settings
max_connections = 200
max_allowed_packet = 256M

# Query Cache
query_cache_size = 0
query_cache_type = 0

[mysql]
default-character-set = utf8mb4
EOF

echo ">>> Restarting MariaDB..."
systemctl restart mariadb

echo ">>> Securing MariaDB..."
mysql_secure_installation
```

**During mysql_secure_installation:**
- Enter current password: [Press Enter]
- Switch to unix_socket authentication: **N**
- Change root password: **Y** - Set: `Pelusa411!` (or your strong password)
- Remove anonymous users: **Y**
- Disallow root login remotely: **Y**
- Remove test database: **Y**
- Reload privilege tables: **Y**

---

### Step 5: Install Redis

```bash
echo ">>> Installing Redis server..."
apt-get install -y redis-server

echo ">>> Starting Redis service..."
systemctl start redis-server
systemctl enable redis-server

echo ">>> Configuring Redis for production..."
sed -i 's/^supervised no/supervised systemd/' /etc/redis/redis.conf
sed -i 's/^# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

echo ">>> Restarting Redis..."
systemctl restart redis-server

echo ">>> Testing Redis:"
redis-cli ping
```

**Expected Output:** `PONG`

---

### Step 6: Install Node.js 18.x & Yarn

```bash
echo ">>> Installing Node.js 18.x..."
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg
echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list

apt-get update -qq
apt-get install -y nodejs

echo ">>> Installing Yarn..."
npm install -g yarn

echo ">>> Verifying installations:"
echo "Node version: $(node --version)"
echo "NPM version: $(npm --version)"
echo "Yarn version: $(yarn --version)"
```

**Expected Versions:**
- Node: v18.20.8
- NPM: 10.8.2+
- Yarn: 1.22.22

---

### Step 7: Install wkhtmltopdf

```bash
cd /tmp
wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
apt-get install -y ./wkhtmltox_0.12.6.1-2.jammy_amd64.deb

echo ">>> Creating symbolic links..."
ln -sf /usr/local/bin/wkhtmltopdf /usr/bin/wkhtmltopdf
ln -sf /usr/local/bin/wkhtmltoimage /usr/bin/wkhtmltoimage

echo ">>> Verifying installation:"
wkhtmltopdf --version

rm -f /tmp/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
cd ~
```

---

### Step 8: Create Frappe User & Setup Environment

```bash
echo ">>> Creating frappe user..."
useradd -m -s /bin/bash frappe
echo "frappe:frappe" | chpasswd

echo ">>> Adding frappe user to sudo group..."
usermod -aG sudo frappe

echo ">>> Configuring passwordless sudo..."
echo "frappe ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/frappe
chmod 440 /etc/sudoers.d/frappe

echo ">>> Creating MySQL user for frappe..."
mysql -u root << 'MYSQL_EOF'
DROP USER IF EXISTS 'frappe'@'localhost';
CREATE USER 'frappe'@'localhost' IDENTIFIED BY 'Pelusa411!';
GRANT ALL PRIVILEGES ON *.* TO 'frappe'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SELECT User, Host FROM mysql.user WHERE User = 'frappe';
MYSQL_EOF

echo ">>> Testing frappe MySQL access..."
mysql -u frappe -p'Pelusa411!' -e "SELECT USER() as 'Current User', DATABASE() as 'Current DB';"

echo ">>> Setting permissions..."
chown -R frappe:frappe /home/frappe
chmod -R 755 /home/frappe
```

---

### Step 9: Install Frappe Bench

```bash
su - frappe << 'EOF'
echo ">>> Installing Frappe Bench CLI..."
pip3 install frappe-bench

echo ">>> Adding bench to PATH..."
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
echo 'export PATH=$PATH:~/.local/bin' >> ~/.profile
source ~/.bashrc

echo ">>> Verifying Bench installation:"
export PATH=$PATH:~/.local/bin
bench --version
EOF
```

**Expected Output:** `5.27.0` (or newer)

---

### Step 10: Initialize Frappe Bench

```bash
su - frappe << 'EOF'
export PATH=$PATH:~/.local/bin

echo ">>> Initializing frappe-bench..."
echo "This will take 5-10 minutes..."

bench init frappe-bench \
  --frappe-branch develop \
  --python python3.11

cd frappe-bench
bench version
EOF
```

**Expected Output:**
```
frappe 15.x.x-develop develop
```

**Note:** This step takes 5-10 minutes and will download and install Frappe Framework.

---

### Step 11: Get ERPNext App

```bash
su - frappe << 'EOF'
export PATH=$PATH:~/.local/bin
cd frappe-bench

echo ">>> Getting ERPNext from GitHub..."
bench get-app erpnext --branch develop

echo ">>> Verifying ERPNext installation:"
cd apps/erpnext
git branch
grep -E "__version__" erpnext/__init__.py | head -3
cd ~/frappe-bench

echo ">>> Apps available:"
bench version --format table
EOF
```

**Expected Output:**
```
+---------+----------------+---------+
| App     | Version        | Branch  |
+---------+----------------+---------+
| erpnext | 16.0.0-dev     | develop |
| frappe  | 15.x.x-develop | develop |
+---------+----------------+---------+
```

---

### Step 12: Create ERPNext Site

```bash
su - frappe << 'EOF'
export PATH=$PATH:~/.local/bin
cd frappe-bench

echo ">>> Creating new site: erp.local..."
bench new-site erp.local \
  --mariadb-root-password 'Pelusa411!' \
  --admin-password 'Admin@2025!'

echo ">>> Site created! Checking configuration:"
cat sites/erp.local/site_config.json
EOF
```

**Important:** Save the Administrator password: `Admin@2025!`

---

### Step 13: Install ERPNext on Site

```bash
su - frappe << 'EOF'
export PATH=$PATH:~/.local/bin
cd frappe-bench

echo ">>> Installing ERPNext on site..."
echo "This will take 5-10 minutes..."

bench --site erp.local install-app erpnext

echo ">>> Clearing cache..."
bench --site erp.local clear-cache

echo ">>> Building assets..."
bench build --app erpnext

echo ">>> Verification:"
bench version --format table
EOF
```

**Expected Output:**
```
+---------+----------------+---------+
| App     | Version        | Branch  |
+---------+----------------+---------+
| erpnext | 16.0.0-dev     | develop |
| frappe  | 15.x.x-develop | develop |
+---------+----------------+---------+
```

---

### Step 14: Run Database Migrations

**IMPORTANT:** This step fixes schema issues.

```bash
su - frappe << 'EOF'
export PATH=$PATH:~/.local/bin
cd frappe-bench

echo ">>> Running database migrations..."
bench --site erp.local migrate

echo ">>> Clearing cache after migration..."
bench --site erp.local clear-cache

echo ">>> Rebuilding assets..."
bench build --app erpnext
EOF
```

This ensures all database tables have the correct columns and structure.

---

### Step 15: Production Setup (Nginx + Supervisor)

```bash
echo ">>> Installing Nginx..."
apt-get install -y nginx

echo ">>> Generating bench configurations..."
su - frappe << 'EOF'
export PATH=$PATH:~/.local/bin
cd frappe-bench

# Generate nginx config
~/.local/bin/bench setup nginx --yes

# Generate supervisor config
~/.local/bin/bench setup supervisor --yes --user frappe

echo "Generated configurations:"
ls -la config/
EOF

echo ">>> Installing configurations..."
mkdir -p /etc/nginx/sites-enabled /etc/nginx/sites-available

# Copy configurations
cp /home/frappe/frappe-bench/config/nginx.conf /etc/nginx/sites-available/frappe-bench.conf
cp /home/frappe/frappe-bench/config/supervisor.conf /etc/supervisor/conf.d/frappe-bench.conf

# Fix nginx log format
sed -i '/http {/a \    log_format main '"'"'$remote_addr - $remote_user [$time_local] "$request" '"'"'\n'"'"'                      $status $body_bytes_sent "$http_referer" '"'"'\n'"'"'                      "$http_user_agent" "$http_x_forwarded_for"'"'"';' /etc/nginx/nginx.conf

# Enable frappe site and disable default
ln -s /etc/nginx/sites-available/frappe-bench.conf /etc/nginx/sites-enabled/frappe-bench.conf
rm -f /etc/nginx/sites-enabled/default

echo ">>> Testing nginx configuration..."
nginx -t

echo ">>> Starting services..."
systemctl reload nginx
supervisorctl reread
supervisorctl update
supervisorctl start all

echo ">>> Checking status..."
supervisorctl status
```

---

### Step 16: Configure Server Name for IP Access

**IMPORTANT:** This step allows access via IP address.

```bash
# Get your server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ">>> Configuring nginx to accept IP: $SERVER_IP"

# Backup original config
cp /etc/nginx/sites-available/frappe-bench.conf /etc/nginx/sites-available/frappe-bench.conf.bak

# Add IP and default catch-all to server_name
sed -i "/server_name/{N;s/server_name\n\t\terp.local/server_name\n\t\t$SERVER_IP\n\t\terp.local\n\t\t_/;}" /etc/nginx/sites-available/frappe-bench.conf

# Verify the change
echo ">>> Server names configured:"
grep -A 4 "server_name" /etc/nginx/sites-available/frappe-bench.conf

# Test and reload nginx
nginx -t && systemctl reload nginx

echo ">>> Testing ERPNext access..."
curl -I http://$SERVER_IP | head -5

echo ""
echo "========================================="
echo "   INSTALLATION COMPLETE!"
echo "========================================="
echo ""
echo "Access ERPNext at: http://$SERVER_IP"
echo "Username: Administrator"
echo "Password: Admin@2025!"
echo ""
echo "========================================="
```

---

## Troubleshooting

### Common Issues & Solutions

#### 1. Database Schema Errors

**Error:** `Unknown column 'tabContact.is_billing_contact'`

**Solution:**
```bash
su - frappe
cd frappe-bench
bench --site erp.local migrate
bench --site erp.local clear-cache
bench build --app erpnext
sudo supervisorctl restart all
```

#### 2. Nginx Shows Default Page

**Solution:**
```bash
# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Add your IP to server_name
SERVER_IP=$(hostname -I | awk '{print $1}')
sed -i "/server_name/{N;s/server_name\n\t\terp.local/server_name\n\t\t$SERVER_IP\n\t\terp.local\n\t\t_/;}" /etc/nginx/sites-available/frappe-bench.conf

# Reload nginx
nginx -t && systemctl reload nginx
```

#### 3. Services Not Starting

**Check logs:**
```bash
# Supervisor logs
tail -f /home/frappe/frappe-bench/logs/web.error.log
tail -f /home/frappe/frappe-bench/logs/worker.error.log

# Nginx logs
tail -f /var/log/nginx/error.log

# Check service status
supervisorctl status
systemctl status nginx
```

**Restart services:**
```bash
sudo supervisorctl restart all
sudo systemctl restart nginx
```

#### 4. Permission Issues

```bash
# Fix bench directory permissions
chown -R frappe:frappe /home/frappe/frappe-bench
chmod -R 755 /home/frappe/frappe-bench

# Restart services
sudo supervisorctl restart all
```

#### 5. Redis Connection Issues

```bash
# Check Redis is running
systemctl status redis-server

# Restart Redis
systemctl restart redis-server

# Verify Redis ports in bench config
cat /home/frappe/frappe-bench/sites/common_site_config.json
```

---

## Post-Installation

### First Login Checklist

1. **Access ERPNext:**
   - URL: `http://YOUR_SERVER_IP`
   - Username: `Administrator`
   - Password: `Admin@2025!`

2. **Change Administrator Password:**
   - Click on user menu → My Settings
   - Change password
   - Update bench password:
     ```bash
     su - frappe
     cd frappe-bench
     bench set-admin-password erp.local --new-password YOUR_NEW_PASSWORD
     ```

3. **Complete Setup Wizard:**
   - Company name
   - Country
   - Fiscal year
   - Chart of accounts
   - Add users

4. **Configure Email:**
   - Setup → Email Domain
   - Setup → Email Account
   - Configure outgoing SMTP

---

## Maintenance & Operations

### Daily Operations

**Check System Status:**
```bash
sudo supervisorctl status
systemctl status nginx
```

**View Logs:**
```bash
# Real-time web logs
tail -f /home/frappe/frappe-bench/logs/web.error.log

# Real-time worker logs
tail -f /home/frappe/frappe-bench/logs/worker.error.log

# Nginx access logs
tail -f /var/log/nginx/access.log
```

**Restart Services:**
```bash
# Restart all ERPNext processes
sudo supervisorctl restart all

# Restart specific service
sudo supervisorctl restart frappe-bench-web:frappe-bench-frappe-web

# Restart nginx
sudo systemctl restart nginx
```

### Backup & Restore

**Manual Backup:**
```bash
su - frappe
cd frappe-bench

# Backup with files
bench --site erp.local backup --with-files

# Backups are stored in:
# /home/frappe/frappe-bench/sites/erp.local/private/backups/
```

**Automated Daily Backups:**
```bash
# Add to frappe user's crontab
su - frappe
crontab -e

# Add this line (backup daily at 2 AM):
0 2 * * * cd /home/frappe/frappe-bench && /home/frappe/.local/bin/bench --site erp.local backup --with-files
```

**Restore from Backup:**
```bash
su - frappe
cd frappe-bench

# List available backups
ls -lh sites/erp.local/private/backups/

# Restore database
bench --site erp.local restore /path/to/backup.sql.gz

# Restore files
bench --site erp.local restore /path/to/files-backup.tar
```

### Updates & Upgrades

**Update ERPNext:**
```bash
su - frappe
cd frappe-bench

# Backup first!
bench --site erp.local backup --with-files

# Update bench
pip3 install --upgrade frappe-bench

# Update apps
bench update --patch

# Or full update (includes git pull)
bench update
```

**Rebuild Assets:**
```bash
su - frappe
cd frappe-bench

bench build --app erpnext
bench restart
```

**Database Migrations:**
```bash
su - frappe
cd frappe-bench

bench --site erp.local migrate
bench --site erp.local clear-cache
bench restart
```

### Performance Tuning

**Increase Worker Processes:**
```bash
# Edit supervisor config
nano /etc/supervisor/conf.d/frappe-bench.conf

# Find and modify:
# numprocs=2  (increase to 4 for more workers)

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
```

**MariaDB Tuning:**
```bash
# Edit MariaDB config
nano /etc/mysql/mariadb.conf.d/erpnext.cnf

# Adjust based on available RAM:
innodb_buffer_pool_size = 2G  # 50-70% of available RAM
max_connections = 300

# Restart MariaDB
systemctl restart mariadb
```

**Redis Tuning:**
```bash
# Edit Redis config
nano /etc/redis/redis.conf

# Adjust memory:
maxmemory 1gb

# Restart Redis
systemctl restart redis-server
```

### Security Hardening

**1. Firewall Configuration:**
```bash
# Install UFW
apt-get install -y ufw

# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

**2. Setup SSL/HTTPS (with Let's Encrypt):**
```bash
# Install certbot
apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
# Test renewal
certbot renew --dry-run
```

**3. Disable Root SSH Login:**
```bash
# Edit SSH config
nano /etc/ssh/sshd_config

# Set:
PermitRootLogin no

# Restart SSH
systemctl restart sshd
```

**4. Enable Fail2Ban:**
```bash
# Install fail2ban
apt-get install -y fail2ban

# Configure for nginx
cat > /etc/fail2ban/jail.local << 'EOF'
[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
EOF

# Restart fail2ban
systemctl restart fail2ban
systemctl enable fail2ban
```

---

## Useful Commands Reference

### Bench Commands

```bash
# Switch to frappe user first
su - frappe
cd frappe-bench

# Site operations
bench --site erp.local migrate           # Update database schema
bench --site erp.local clear-cache       # Clear cache
bench --site erp.local clear-website-cache  # Clear website cache
bench --site erp.local backup            # Backup database
bench --site erp.local backup --with-files  # Backup database + files
bench --site erp.local restore [file]    # Restore from backup

# Console access
bench --site erp.local console           # Python console
bench --site erp.local mariadb          # MySQL console

# Service management
bench restart                            # Restart web services
bench start                              # Start development server (not for production)

# Build and update
bench build --app erpnext                # Rebuild assets
bench update --patch                     # Update apps (patch only)
bench update                             # Full update

# App management
bench get-app [app-name]                 # Download new app
bench --site erp.local install-app [app] # Install app on site
bench --site erp.local uninstall-app [app] # Uninstall app
```

### System Commands

```bash
# Service status
sudo supervisorctl status                # All ERPNext processes
sudo systemctl status nginx              # Nginx status
sudo systemctl status mariadb            # Database status
sudo systemctl status redis-server       # Redis status

# Service control
sudo supervisorctl restart all           # Restart all processes
sudo supervisorctl start all             # Start all processes
sudo supervisorctl stop all              # Stop all processes

# View logs
tail -f /home/frappe/frappe-bench/logs/web.error.log
tail -f /home/frappe/frappe-bench/logs/worker.error.log
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Disk usage
df -h                                    # Check disk space
du -sh /home/frappe/frappe-bench         # Check bench size
du -sh /var/lib/mysql                    # Check database size
```

---

## Important File Locations

### Configuration Files
- **Site Config:** `/home/frappe/frappe-bench/sites/erp.local/site_config.json`
- **Common Config:** `/home/frappe/frappe-bench/sites/common_site_config.json`
- **Nginx Config:** `/etc/nginx/sites-available/frappe-bench.conf`
- **Supervisor Config:** `/etc/supervisor/conf.d/frappe-bench.conf`
- **MariaDB Config:** `/etc/mysql/mariadb.conf.d/erpnext.cnf`
- **Redis Config:** `/etc/redis/redis.conf`

### Data Directories
- **Bench Root:** `/home/frappe/frappe-bench/`
- **Apps:** `/home/frappe/frappe-bench/apps/`
- **Sites:** `/home/frappe/frappe-bench/sites/`
- **Site Files:** `/home/frappe/frappe-bench/sites/erp.local/`
- **Private Files:** `/home/frappe/frappe-bench/sites/erp.local/private/`
- **Public Files:** `/home/frappe/frappe-bench/sites/erp.local/public/`
- **Backups:** `/home/frappe/frappe-bench/sites/erp.local/private/backups/`

### Log Files
- **Web Logs:** `/home/frappe/frappe-bench/logs/web.error.log`
- **Worker Logs:** `/home/frappe/frappe-bench/logs/worker.error.log`
- **Bench Logs:** `/home/frappe/frappe-bench/logs/bench.log`
- **Nginx Error:** `/var/log/nginx/error.log`
- **Nginx Access:** `/var/log/nginx/access.log`
- **MariaDB Error:** `/var/log/mysql/error.log`

---

## Version Information

This guide was tested with:

- **OS:** Ubuntu 22.04.5 LTS
- **Python:** 3.11.14
- **Node.js:** 18.20.8
- **MariaDB:** 10.6+
- **Redis:** 6.0.16
- **Nginx:** 1.18.0
- **Frappe Bench:** 5.27.0
- **Frappe Framework:** 15.x.x-develop
- **ERPNext:** 16.0.0-dev

---

## Support & Resources

- **Official Documentation:** https://docs.erpnext.com/
- **Frappe Framework Docs:** https://frappeframework.com/docs/
- **Community Forum:** https://discuss.frappe.io/
- **GitHub Issues:** https://github.com/frappe/erpnext/issues
- **Frappe School (Training):** https://frappe.school

---

## License

ERPNext is licensed under GNU General Public License v3.0

---

**Document Version:** 2.0
**Last Updated:** December 18, 2025
**Author:** ERPNext Installation Guide for CT/LXC
