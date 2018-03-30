import frappe

def execute():
	for doctype in ("Sales Order", "Purchase Order"):
		for doc in frappe.get_all(doctype, filters={"docstatus": 1}):
			doc = frappe.get_doc(doctype, doc.name)
			doc.set_status(update=True)
