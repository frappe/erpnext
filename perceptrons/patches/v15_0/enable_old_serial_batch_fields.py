import frappe


def execute():
	sabb = frappe.get_all("Serial and Batch Bundle", filters={"docstatus": ("<", 2)}, limit=1)
	if not sabb:
		frappe.db.set_single_value("Stock Settings", "use_serial_batch_fields", 1)
