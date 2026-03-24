import frappe


def execute():
	if frappe.db.has_table("Tax Withholding Category") and frappe.db.has_column(
		"Tax Withholding Category", "round_off_tax_amount"
	):
		tax_withholding_category = frappe.qb.DocType("Tax Withholding Category")
		(
			frappe.qb.update(tax_withholding_category)
			.set(tax_withholding_category.round_off_tax_amount, 0)
			.where(tax_withholding_category.round_off_tax_amount.isnull())
		).run()
