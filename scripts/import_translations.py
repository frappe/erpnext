"""
Import translations from CSV into Frappe's Translation doctype.
Run via: bench --site frontend run-doc-method --method import_all
Or: bench --site frontend execute erpnext.scripts.import_translations.import_all
"""
import frappe
import csv
import os


def import_all():
    """Import Kurdish and Arabic translations from CSV files."""
    base = os.path.dirname(os.path.abspath(__file__))

    # Kurdish
    ku_csv = os.path.join(base, "frappe_translations_ku.csv")
    if os.path.exists(ku_csv):
        count = _import_csv(ku_csv, "ku")
        print(f"Kurdish: {count} translations imported")
    else:
        print(f"Kurdish CSV not found at {ku_csv}")

    # Arabic
    ar_csv = os.path.join(base, "frappe_translations_ar.csv")
    if os.path.exists(ar_csv):
        count = _import_csv(ar_csv, "ar")
        print(f"Arabic: {count} translations imported")
    else:
        print(f"Arabic CSV not found at {ar_csv}")

    frappe.db.commit()

    # Clear translation cache
    frappe.cache.delete_value("boot_translations")
    for lang in ["ku", "ar"]:
        frappe.cache.delete_value(f"translation_assets:{lang}")
        frappe.cache.delete_keys(f"lang:{lang}*")
        frappe.cache.delete_keys(f"translated_text:{lang}*")

    print("Cache cleared. Translations should now be visible.")


def _import_csv(csv_path, lang):
    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row.get("source", "").strip()
            translated = row.get("translated", "").strip()
            context = row.get("context", "").strip() or None
            if not source or not translated:
                continue

            existing = frappe.db.get_value(
                "Translation",
                {"language": lang, "source_text": source},
                "name"
            )
            if existing:
                frappe.db.set_value("Translation", existing, "translated_text", translated)
            else:
                doc = frappe.get_doc({
                    "doctype": "Translation",
                    "language": lang,
                    "source_text": source,
                    "translated_text": translated,
                    "context": context,
                    "contributed": 0
                })
                doc.flags.ignore_permissions = True
                doc.insert()
            count += 1
    return count
