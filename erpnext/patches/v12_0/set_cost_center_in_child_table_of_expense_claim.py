import frappe
def execute():
	frappe.reload_doc('hr', 'doctype', 'expense_claim_detail')
	frappe.db.sql("""
		UPDATE `tabExpense Claim Detail` child, `tabExpense Claim` par
		SET child.cost_center = par.cost_center
		WHERE child.parent = par.name
	""")