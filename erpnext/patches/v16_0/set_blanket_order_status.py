import frappe


def execute():
	for docstatus, status in ((0, "Draft"), (1, "Submitted"), (2, "Cancelled")):
		frappe.db.set_value(
			"Blanket Order", {"docstatus": docstatus}, "status", status, update_modified=False
		)
