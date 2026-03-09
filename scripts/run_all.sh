#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ZirakERP - ONE COMMAND language setup
# Run from: ~/Desktop/ZirakERP/docker/
# Usage:    bash ../scripts/run_all.sh
# ═══════════════════════════════════════════════════════════

cd "$(dirname "$0")/../docker"

echo ""
echo "═══════════════════════════════════════════════"
echo "  ZirakERP Language Import"
echo "═══════════════════════════════════════════════"

# Make sure containers are running
echo ""
echo "[1/5] Starting containers..."
docker compose up -d

echo ""
echo "[2/5] Waiting for backend to be ready..."
sleep 10

# Create scripts dir and copy files into container
echo ""
echo "[3/5] Copying translation files into container..."
docker compose exec backend mkdir -p /home/frappe/frappe-bench/apps/erpnext/scripts

docker compose cp ../scripts/frappe_translations_ku.csv backend:/home/frappe/frappe-bench/apps/erpnext/scripts/frappe_translations_ku.csv
docker compose cp ../scripts/frappe_translations_ar.csv backend:/home/frappe/frappe-bench/apps/erpnext/scripts/frappe_translations_ar.csv
docker compose cp ../scripts/do_import.py backend:/home/frappe/frappe-bench/apps/erpnext/scripts/do_import.py
docker compose cp ../erpnext/locale/ku.po backend:/home/frappe/frappe-bench/apps/erpnext/erpnext/locale/ku.po

echo ""
echo "[4/5] Importing translations into database..."
docker compose exec backend bench --site frontend python /home/frappe/frappe-bench/apps/erpnext/scripts/do_import.py

echo ""
echo "[5/5] Clearing cache and restarting..."
docker compose exec backend bench --site frontend clear-cache
docker compose restart backend frontend websocket

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ Done! Wait ~15 seconds, then open:"
echo "  http://localhost:8080"
echo ""
echo "  Login: Administrator / admin"
echo "  Change language: Settings → My Settings → Language"
echo "═══════════════════════════════════════════════"
