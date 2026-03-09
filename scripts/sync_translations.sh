#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ZirakERP - Quick sync: download translation CSVs from running ERP
# No Docker access needed - downloads via HTTP from localhost:8080
# Usage: bash scripts/sync_translations.sh
# ═══════════════════════════════════════════════════════════

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_URL="http://localhost:8080"

echo "Downloading translations from $BASE_URL..."

curl -s -o "$SCRIPTS_DIR/frappe_translations_ku.csv" "$BASE_URL/files/frappe_translations_ku.csv"
curl -s -o "$SCRIPTS_DIR/frappe_translations_ar.csv" "$BASE_URL/files/frappe_translations_ar.csv"

echo "  Kurdish: $(wc -l < "$SCRIPTS_DIR/frappe_translations_ku.csv") lines"
echo "  Arabic:  $(wc -l < "$SCRIPTS_DIR/frappe_translations_ar.csv") lines"
echo "✅ Done!"
