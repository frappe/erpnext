import frappe


def execute():
	frappe.db.sql(
		"""
		DELETE FROM `tabAsset Movement Item`
		WHERE parent NOT IN (SELECT name FROM `tabAsset Movement`)
		"""
	)
