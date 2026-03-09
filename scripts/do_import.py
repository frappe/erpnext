import frappe, csv, os

def run():
    base = os.path.dirname(os.path.abspath(__file__))
    for lang, fn in [("ku", "frappe_translations_ku.csv"), ("ar", "frappe_translations_ar.csv")]:
        path = os.path.join(base, fn)
        if not os.path.exists(path):
            print(f"SKIP {lang}: file not found at {path}")
            continue
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                src = row["source"].strip()
                tr = row["translated"].strip()
                if not src or not tr:
                    continue
                ex = frappe.db.get_value("Translation", {"language": lang, "source_text": src}, "name")
                if ex:
                    frappe.db.set_value("Translation", ex, "translated_text", tr)
                else:
                    frappe.get_doc({"doctype": "Translation", "language": lang, "source_text": src, "translated_text": tr, "contributed": 0}).insert(ignore_permissions=True)
                count += 1
        print(f"{lang}: {count} translations imported")
    frappe.db.commit()
    print("DONE - translations committed to database")

run()
