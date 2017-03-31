import frappe

def execute():
    old_name = 'LetterHead'
    new_name = 'LetterHead'
    if frappe.db.table_exists(old_name) and not frappe.db.table_exists(new_name):
        frappe.rename_doc("DocType", old_name, new_name)
