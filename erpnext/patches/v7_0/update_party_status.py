import frappe
from erpnext.accounts.party_status import update_status

def execute():
	for doctype in ('Customer', 'Supplier'):
		frappe.reload_doctype(doctype)
		for doc in frappe.get_all(doctype):
			doc = frappe.get_doc(doctype, doc.name)
			update_status(doc)