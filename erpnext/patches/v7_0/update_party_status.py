import frappe

def execute():
	for doctype in ('Customer', 'Supplier'):
		for doc in frappe.get_all(doctype):
			doc = frappe.get_doc(doctype, doc.name)
			doc.update_status()