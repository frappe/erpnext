import frappe


def execute():
	frappe.reload_doc("selling", "doctype", "sales_order")

	for order in frappe.get_all("Sales Order", {"status": "Completed"}):
		frappe.db.set_value("Sales Order", order.name, "is_completed", True, update_modified=False)
		frappe.db.commit()