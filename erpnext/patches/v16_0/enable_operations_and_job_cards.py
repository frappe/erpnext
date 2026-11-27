import frappe


def execute():
	if not frappe.get_all("BOM", filters={"with_operations": 1}, limit=1) and not frappe.get_all(
		"Job Card", limit=1
	):
		return

	frappe.db.set_single_value("Manufacturing Settings", "enable_operations_and_job_cards", 1)
