import frappe


def execute():
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_receipt')
	docs = frappe.get_all("Vehicle Invoice Receipt")
	for d in docs:
		doc = frappe.get_doc("Vehicle Invoice Receipt", d.name)
		doc.set_status(update=True, update_modified=False)
		doc.clear_cache()
