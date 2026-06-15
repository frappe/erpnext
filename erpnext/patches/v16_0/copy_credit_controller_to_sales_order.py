import frappe


def execute():
	credit_controller = frappe.db.get_single_value("Accounts Settings", "credit_controller")
	if credit_controller:
		frappe.db.set_single_value(
			"Accounts Settings", "credit_controller_for_sales_order", credit_controller
		)
