import frappe


def execute():
	if not frappe.db.exists("BOM", {"docstatus": 1}):
		return

	# Added is_stock_item to handle Read Only based on condition for the rate field
	frappe.db.sql(
		"""
		UPDATE
			`tabBOM Item` boi,
			`tabItem` i
		SET
			boi.is_stock_item = i.is_stock_item
		WHERE
			boi.item_code = i.name
	"""
	)
