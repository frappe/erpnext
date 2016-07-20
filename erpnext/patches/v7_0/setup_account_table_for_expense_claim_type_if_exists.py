from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("hr", "doctype", "expense_claim_type")
	frappe.reload_doc("hr", "doctype", "expense_claim_account")
	
	for expense_claim_type in frappe.get_all("Expense Claim Type", fields=["name", "default_account"]):
		if expense_claim_type.default_account:
			doc = frappe.get_doc("Expense Claim Type", expense_claim_type.name)
			doc.append("accounts", {
				"company": frappe.db.get_value("Account", expense_claim_type.default_account, "company"),
				"default_account": expense_claim_type.default_account,
			})
			doc.save(ignore_permissions=True)