import frappe


def execute():
	"""
	- Don't use batchwise valuation for existing batches.
	- Only batches created after this patch shoule use it.
	"""

	# To set the batchwise condition
	frappe.reload_doc("stock", "doctype", "batch")
	frappe.db.sql("""
		UPDATE `tabBatch`
		SET use_batchwise_valuation=0
	""")

	# To prevent fetching batchwise SLEs for valuation
	frappe.reload_doc("stock", "doctype", "stock_ledger_entry")
	frappe.db.sql("""
		UPDATE `tabStock Ledger Entry`
		SET use_batchwise_valuation=0
	""")
