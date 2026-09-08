import frappe

from erpnext.stock.serial_batch_identity import SerialBatchIdentity


def execute():
	checked = []
	for doctype in ("Serial No", "Batch"):
		identity = SerialBatchIdentity(doctype)
		if not identity.has_constraint():
			identity.validate_existing_numbers()
			checked.append(doctype)

	previous = frappe.flags.serial_batch_preflight
	try:
		frappe.flags.serial_batch_preflight = checked
		for doctype in ("Serial No", "Batch"):
			frappe.reload_doc("stock", "doctype", frappe.scrub(doctype), force=True)
	finally:
		frappe.flags.serial_batch_preflight = previous
