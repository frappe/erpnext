import frappe

from erpnext.stock.serial_batch_identity import SerialBatchIdentity


def execute():
	# Reload also drops the former single-field unique indexes on both database engines.
	for doctype in ("Serial No", "Batch"):
		frappe.reload_doc("stock", "doctype", frappe.scrub(doctype), force=True)
		SerialBatchIdentity(doctype).sync_constraint()
