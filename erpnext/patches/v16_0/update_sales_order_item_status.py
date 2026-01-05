import frappe


def execute():
	frappe.db.auto_commit_on_many_writes = 1
	sales_order = frappe.qb.DocType("Sales Order")
	sales_order_item = frappe.qb.DocType("Sales Order Item")

	try:
		frappe.qb.update(sales_order_item).join(sales_order).on(
			sales_order.name == sales_order_item.parent
		).set(sales_order_item.is_closed, 1).where(
			(sales_order.name == sales_order_item.parent)
			& (sales_order.status == "Closed")
			& (sales_order_item.is_closed == 0)
		).run()
	finally:
		frappe.db.auto_commit_on_many_writes = 0
