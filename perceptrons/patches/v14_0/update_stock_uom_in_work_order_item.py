import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE
			`tabWork Order Item`, `tabItem`
		SET
			`tabWork Order Item`.stock_uom = `tabItem`.stock_uom
		WHERE
			`tabWork Order Item`.item_code = `tabItem`.name
			AND `tabWork Order Item`.docstatus = 1
	"""
	)
