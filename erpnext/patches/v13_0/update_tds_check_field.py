import frappe


def condition():
	return frappe.db.has_table("Tax Withholding Category") \
		and frappe.db.has_column("Tax Withholding Category", "round_off_tax_amount")

def execute():
	frappe.db.sql("""
		UPDATE `tabTax Withholding Category` set round_off_tax_amount = 0
		WHERE round_off_tax_amount IS NULL
	""")
