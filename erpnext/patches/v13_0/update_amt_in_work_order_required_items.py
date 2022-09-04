import frappe


def execute():
	"""Correct amount in child table of required items table."""

	frappe.reload_doc("manufacturing", "doctype", "work_order")
	frappe.reload_doc("manufacturing", "doctype", "work_order_item")

	frappe.db.sql("""UPDATE `tabWork Order Item` SET amount = rate * required_qty""")
