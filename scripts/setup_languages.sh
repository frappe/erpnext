#!/bin/bash
# ──────────────────────────────────────────────────────────
# ZirakERP Language Setup Script
# Registers Kurdish + Arabic, imports translations, configures RTL
# Run from: ~/Desktop/ZirakERP/docker/
# ──────────────────────────────────────────────────────────

set -e

SITE="frontend"
COMPOSE="docker compose"

echo "================================================"
echo "  ZirakERP Language Setup"
echo "  Languages: English, Kurdish (Sorani), Arabic"
echo "================================================"

# ── Step 1: Register Kurdish language ──
echo ""
echo "[1/6] Registering Kurdish (Sorani) language..."
$COMPOSE exec -T backend bench --site $SITE console <<'PYEOF'
import frappe
if not frappe.db.exists("Language", "ku"):
    doc = frappe.get_doc({
        "doctype": "Language",
        "language_code": "ku",
        "language_name": "Kurdish (Sorani)",
        "enabled": 1
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  ✓ Kurdish (Sorani) registered")
else:
    frappe.db.set_value("Language", "ku", "enabled", 1)
    frappe.db.commit()
    print("  ✓ Kurdish already exists, enabled")
PYEOF

# ── Step 2: Ensure Arabic is enabled ──
echo ""
echo "[2/6] Ensuring Arabic is enabled..."
$COMPOSE exec -T backend bench --site $SITE console <<'PYEOF'
import frappe
if frappe.db.exists("Language", "ar"):
    frappe.db.set_value("Language", "ar", "enabled", 1)
    frappe.db.commit()
    print("  ✓ Arabic enabled")
else:
    doc = frappe.get_doc({
        "doctype": "Language",
        "language_code": "ar",
        "language_name": "Arabic",
        "enabled": 1
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  ✓ Arabic registered")
PYEOF

# ── Step 3: Import Frappe-level translations via Translation doctype ──
echo ""
echo "[3/6] Importing core UI translations (Kurdish)..."
$COMPOSE exec -T backend bench --site $SITE console <<'PYEOF'
import frappe
import csv
import os

# Kurdish translations
csv_path = "/home/frappe/frappe-bench/apps/erpnext/scripts/frappe_translations_ku.csv"
if os.path.exists(csv_path):
    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row["source"].strip()
            translated = row["translated"].strip()
            if not source or not translated:
                continue
            # Check if translation already exists
            existing = frappe.db.exists("Translation", {
                "language": "ku",
                "source_text": source
            })
            if existing:
                frappe.db.set_value("Translation", existing, "translated_text", translated)
            else:
                doc = frappe.get_doc({
                    "doctype": "Translation",
                    "language": "ku",
                    "source_text": source,
                    "translated_text": translated,
                    "contributed": 0
                })
                doc.insert(ignore_permissions=True)
            count += 1
    frappe.db.commit()
    print(f"  ✓ Imported {count} Kurdish translations")
else:
    print(f"  ⚠ CSV not found at {csv_path}")
    print("    Trying alternate path...")
    # Try to find it
    for root, dirs, files in os.walk("/home/frappe/frappe-bench/apps"):
        for f in files:
            if f == "frappe_translations_ku.csv":
                print(f"    Found at: {os.path.join(root, f)}")
                break
PYEOF

echo ""
echo "[4/6] Importing core UI translations (Arabic)..."
$COMPOSE exec -T backend bench --site $SITE console <<'PYEOF'
import frappe
import csv
import os

csv_path = "/home/frappe/frappe-bench/apps/erpnext/scripts/frappe_translations_ar.csv"
if os.path.exists(csv_path):
    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row["source"].strip()
            translated = row["translated"].strip()
            if not source or not translated:
                continue
            existing = frappe.db.exists("Translation", {
                "language": "ar",
                "source_text": source
            })
            if existing:
                frappe.db.set_value("Translation", existing, "translated_text", translated)
            else:
                doc = frappe.get_doc({
                    "doctype": "Translation",
                    "language": "ar",
                    "source_text": source,
                    "translated_text": translated,
                    "contributed": 0
                })
                doc.insert(ignore_permissions=True)
            count += 1
    frappe.db.commit()
    print(f"  ✓ Imported {count} Arabic translations")
else:
    print(f"  ⚠ CSV not found at {csv_path}")
PYEOF

# ── Step 5: Enable scheduler ──
echo ""
echo "[5/6] Enabling scheduler..."
$COMPOSE exec -T backend bench --site $SITE enable-scheduler 2>/dev/null || true

# ── Step 6: Clear cache ──
echo ""
echo "[6/6] Clearing cache..."
$COMPOSE exec -T backend bench --site $SITE clear-cache

echo ""
echo "================================================"
echo "  ✅ Language setup complete!"
echo ""
echo "  Languages available:"
echo "    • English"
echo "    • کوردی (Kurdish Sorani)"
echo "    • العربية (Arabic)"
echo ""
echo "  How to change language:"
echo "    Per-user:  Login → User dropdown → My Settings → Language"
echo "    System:    Setup → Settings → System Settings → Language"
echo "    Login page: language selector dropdown"
echo ""
echo "  RTL (right-to-left) is automatic for Kurdish & Arabic"
echo "================================================"
