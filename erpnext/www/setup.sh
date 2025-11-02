#!/usr/bin/env bash
set -e

echo "🔧 Installing system dependencies..."
apt-get update -y
apt-get install -y mariadb-server redis-server curl gnupg python3 python3-pip python3-venv npm

echo "⚙️ Installing frappe-bench..."
pip install frappe-bench

echo "📦 Initializing bench..."
bench init --frappe-branch ${FRAPPE_BRANCH:-version-15} frappe-bench
cd frappe-bench

echo "🌐 Creating new site ${SITE_NAME}..."
bench new-site ${SITE_NAME} --admin-password ${ADMIN_PASSWORD:-admin} --db-root-password ${DB_ROOT_PASSWORD:-root}

echo "🧱 Getting ERPNext app..."
bench get-app --branch ${ERPNEXT_BRANCH:-version-15} erpnext

echo "🏗️ Installing ERPNext..."
bench --site ${SITE_NAME} install-app erpnext

echo "✅ Setup completed successfully!"

