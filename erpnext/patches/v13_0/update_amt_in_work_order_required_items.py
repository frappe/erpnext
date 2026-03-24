import frappe


def execute():
	"""Correct amount in child table of required items table."""

	frappe.reload_doc("manufacturing", "doctype", "work_order")
	frappe.reload_doc("manufacturing", "doctype", "work_order_item")

	for row in frappe.get_all("Work Order Item", fields=["name", "rate", "required_qty"]):
		frappe.db.set_value(
			"Work Order Item",
			row.name,
			"amount",
			(row.rate or 0.0) * (row.required_qty or 0.0),
			update_modified=False,
		)
