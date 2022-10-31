import frappe


def execute():
	frappe.reload_doc("loan_management", "doctype", "loan")
	frappe.reload_doc("loan_management", "doctype", "loan_type")

	loan = frappe.qb.DocType("Loan")
	loan_type = frappe.qb.DocType("Loan Type")

	frappe.qb.update(loan_type).set(
		loan_type.repayment_schedule_type, "Monthly as per repayment start date"
	).where(loan_type.is_term_loan == 1).run()

	frappe.qb.update(loan).set(
		loan.repayment_schedule_type, "Monthly as per repayment start date"
	).where(loan.is_term_loan == 1).run()
