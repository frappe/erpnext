import frappe


def execute():
	frappe.db.sql(
		"""
			UPDATE
					`tabPurchase Invoice Item`
			INNER JOIN
					`tabPurchase Invoice`
			ON
					`tabPurchase Invoice`.name = `tabPurchase Invoice Item`.parent
			SET
					`tabPurchase Invoice Item`.apply_tds = 1
			WHERE
					`tabPurchase Invoice`.apply_tds = 1
					and `tabPurchase Invoice`.docstatus = 1
			"""
	)

	frappe.db.sql(
		"""
			UPDATE `tabPurchase Invoice`
			SET tax_withholding_net_total = net_total,
			base_tax_withholding_net_total = base_net_total
			WHERE apply_tds = 1 and docstatus = 1"""
	)
