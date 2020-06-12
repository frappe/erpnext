import frappe


def execute():
	frappe.reload_doc("stock", "doctype", "batch")

	for batch in frappe.get_all("Batch", fields=["name", "batch_id"]):
		batch_qty = frappe.db.get_value("Stock Ledger Entry",
			{"docstatus": 1, "batch_no": batch.batch_id, "is_cancelled": 0},
			"sum(actual_qty)") or 0.0
		frappe.db.set_value("Batch", batch.name, "batch_qty", batch_qty, update_modified=False)
