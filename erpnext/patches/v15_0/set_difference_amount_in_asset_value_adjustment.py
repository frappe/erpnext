import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE
			`tabAsset Value Adjustment`
		SET
			difference_amount = -1*difference_amount
		WHERE
			docstatus != 2
	"""
	)
