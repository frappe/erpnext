import frappe


def execute():

	frappe.reload_doc("loan_management", "doctype", "loan_type")
	frappe.reload_doc("loan_management", "doctype", "loan")

	loan_type = frappe.qb.DocType("Loan Type")
	loan = frappe.qb.DocType("Loan")

	frappe.qb.update(loan_type).set(loan_type.disbursement_account, loan_type.payment_account).run()

	frappe.qb.update(loan).set(loan.disbursement_account, loan.payment_account).run()
