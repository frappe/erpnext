import frappe


def execute():

	frappe.db.sql("""
		UPDATE `tabLower Deduction Certificate` l, `tabSupplier` s
		SET l.tax_withholding_category = s.tax_withholding_category
		WHERE l.supplier = s.name
	""")