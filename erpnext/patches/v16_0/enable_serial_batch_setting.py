import frappe


def execute():
	if not frappe.get_all("Serial No", limit=1) and not frappe.get_all("Batch", limit=1):
		return

	frappe.db.set_single_value("Stock Settings", "enable_serial_and_batch_no_for_item", 1)
	frappe.db.set_default("enable_serial_and_batch_no_for_item", 1)
