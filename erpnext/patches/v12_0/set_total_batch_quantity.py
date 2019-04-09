import frappe


def execute():
	for batch in frappe.get_all("Batch", fields=["name", "batch_id"]):
		batch_qty = frappe.db.get_value("Stock Ledger Entry", {"docstatus": 1, "batch_no": batch.batch_id}, "sum(actual_qty)")
		frappe.db.set_value("Batch", batch.name, "batch_qty", batch_qty, update_modified=False)
