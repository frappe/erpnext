#!/usr/bin/env python3
"""
Setup script to register Kurdish and configure languages in Frappe/ZirakERP.
Run this INSIDE the Docker container:
  docker compose exec backend bench --site frontend execute scripts/setup_languages.py

Or run via bench console:
  docker compose exec backend bench --site frontend console
  Then paste the setup_languages() function content.
"""

import frappe


def setup_languages():
    """Register Kurdish language and configure language options."""

    # ── 1. Add Kurdish to Frappe's language list ──
    # Check if Kurdish already exists
    if not frappe.db.exists("Language", "ku"):
        lang = frappe.get_doc({
            "doctype": "Language",
            "language_code": "ku",
            "language_name": "Kurdish (Sorani)",
            "enabled": 1,
            "flag": "🇮🇶",
        })
        lang.insert(ignore_permissions=True)
        print("✓ Kurdish (Sorani) language registered")
    else:
        # Enable it if disabled
        frappe.db.set_value("Language", "ku", "enabled", 1)
        print("✓ Kurdish (Sorani) already exists, enabled")

    # ── 2. Ensure Arabic is enabled ──
    if frappe.db.exists("Language", "ar"):
        frappe.db.set_value("Language", "ar", "enabled", 1)
        print("✓ Arabic enabled")
    else:
        lang = frappe.get_doc({
            "doctype": "Language",
            "language_code": "ar",
            "language_name": "Arabic",
            "enabled": 1,
            "flag": "🇸🇦",
        })
        lang.insert(ignore_permissions=True)
        print("✓ Arabic language registered")

    # ── 3. Ensure English is enabled ──
    if frappe.db.exists("Language", "en"):
        frappe.db.set_value("Language", "en", "enabled", 1)
        print("✓ English enabled")

    # ── 4. Enable scheduler (needed for background jobs) ──
    frappe.utils.scheduler.enable_scheduler()
    print("✓ Scheduler enabled")

    # ── 5. Import translations from PO files ──
    from frappe.translate import import_translations
    try:
        import_translations("ku")
        print("✓ Kurdish translations imported")
    except Exception as e:
        print(f"⚠ Kurdish translation import: {e}")
        print("  (Translations will be loaded from PO files automatically)")

    try:
        import_translations("ar")
        print("✓ Arabic translations imported")
    except Exception as e:
        print(f"⚠ Arabic translation import: {e}")
        print("  (Translations will be loaded from PO files automatically)")

    frappe.db.commit()
    print("\n✅ Language setup complete!")
    print("   Available languages: English, Kurdish (Sorani), Arabic")
    print("   Users can change language in: Settings > Language")
    print("   Login page language can be changed from the language dropdown")


if __name__ == "__main__":
    setup_languages()
