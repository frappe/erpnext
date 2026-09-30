import frappe


def execute():
	"""Tick every business module on existing companies, so nothing hides after the update."""
	from erpnext.hooks import business_modules

	company = frappe.qb.DocType("Company")
	query = frappe.qb.update(company)
	for module in business_modules:
		query = query.set(company[module["fieldname"]], 1)
	query.run()
