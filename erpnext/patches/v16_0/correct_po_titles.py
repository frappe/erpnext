import frappe


def execute():
	"""
	This patch corrects the titles of purchase orders that were set to
	the text string "{supplier_name}" instead of the actual supplier name.
	"""

	purchase_order = frappe.qb.DocType("Purchase Order")
	(
		frappe.qb.update(purchase_order)
		.set(purchase_order.title, purchase_order.supplier_name)
		.where(purchase_order.title == "{supplier_name}")
	).run()
