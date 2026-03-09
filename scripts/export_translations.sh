#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ZirakERP - Export translations from database to CSV files
# Run from: ~/Desktop/ZirakERP/docker/
# Usage:    bash ../scripts/export_translations.sh
# ═══════════════════════════════════════════════════════════

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$(dirname "$0")/../docker"

COMPOSE="docker compose"
SITE="frontend"

echo ""
echo "═══════════════════════════════════════════════"
echo "  ZirakERP Translation Export"
echo "═══════════════════════════════════════════════"

echo ""
echo "[1/3] Exporting translations from database..."

# Export inside the container using bench console
$COMPOSE exec -T backend bench --site $SITE console <<'PYEOF'
import csv, frappe

for lang, filename in [("ku", "frappe_translations_ku.csv"), ("ar", "frappe_translations_ar.csv")]:
    translations = frappe.get_all(
        "Translation",
        filters={"language": lang},
        fields=["source_text", "translated_text"],
        order_by="source_text asc",
        limit_page_length=0
    )
    # Deduplicate
    seen = {}
    for t in translations:
        if t.source_text not in seen:
            seen[t.source_text] = t.translated_text

    path = f"/home/frappe/frappe-bench/apps/erpnext/scripts/{filename}"
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "translated", "context"])
        for src in sorted(seen.keys()):
            w.writerow([src, seen[src], ""])
    print(f"  {lang}: {len(seen)} unique translations -> {path}")

PYEOF

echo ""
echo "[2/3] Copying CSV files from container to project..."

$COMPOSE cp backend:/home/frappe/frappe-bench/apps/erpnext/scripts/frappe_translations_ku.csv "$SCRIPTS_DIR/frappe_translations_ku.csv"
$COMPOSE cp backend:/home/frappe/frappe-bench/apps/erpnext/scripts/frappe_translations_ar.csv "$SCRIPTS_DIR/frappe_translations_ar.csv"

echo ""
echo "[3/3] Verifying exported files..."
echo "  Kurdish: $(wc -l < "$SCRIPTS_DIR/frappe_translations_ku.csv") lines"
echo "  Arabic:  $(wc -l < "$SCRIPTS_DIR/frappe_translations_ar.csv") lines"

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ Export complete!"
echo "  Files saved to:"
echo "    scripts/frappe_translations_ku.csv"
echo "    scripts/frappe_translations_ar.csv"
echo "═══════════════════════════════════════════════"
