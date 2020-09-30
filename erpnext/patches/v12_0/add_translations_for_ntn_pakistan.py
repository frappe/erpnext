import frappe

def execute():
    country = frappe.db.get_single_value("Global Defaults", "country")

    if country != "Pakistan":
        return

    translations = [
        ('Tax Id: ', 'NTN: '),
        ('Tax ID: ', 'NTN: '),
        ('Tax ID', 'NTN'),
        ('Tax Id', 'NTN')
    ]

    for source, translated in translations:
        existing = frappe.db.get_all("Translation", filters={'source_name': source, "language": "en"}, fields=['name', 'source_name'])
        existing = [d for d in existing if d.source_name == source]
        if existing:
            docs = [frappe.get_doc("Translation", d.name) for d in existing]
        else:
            doc = frappe.new_doc("Translation")
            doc.source_name = source
            doc.language = "en"
            docs = [doc]

        for doc in docs:
            doc.target_name = translated
            doc.save()