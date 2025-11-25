import frappe

def execute():
    draft_journals = frappe.get_all('Journal Entry', filters={'docstatus': 0}, fields=['name'])
    updated = 0
    for je in draft_journals:
        doc = frappe.get_doc('Journal Entry', je.name)
        first_debit_account = None
        for entry in doc.accounts:
            if entry.debit > 0:
                first_debit_account = entry.account
                break
        
        if not first_debit_account:
            continue  
        
        old_title = doc.title
        new_title = first_debit_account
        
        if new_title != old_title:
            doc.title = new_title
            doc.save(ignore_permissions=True)
            updated += 1
            print(f"Updated {doc.name}: '{old_title}' -> '{new_title}'")
    frappe.db.commit()
    print(f"Total draft Journal Entries updated: {updated}")