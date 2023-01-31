import frappe


def execute():
	ld = frappe.qb.DocType("Loan Disbursement").as_("ld")
	lr = frappe.qb.DocType("Loan Repayment").as_("lr")
	loan = frappe.qb.DocType("Loan")

	frappe.qb.update(ld).inner_join(loan).on(loan.name == ld.against_loan).set(
		ld.disbursement_account, loan.disbursement_account
	).set(ld.loan_account, loan.loan_account).where(ld.docstatus < 2).run()

	frappe.qb.update(lr).inner_join(loan).on(loan.name == lr.against_loan).set(
		lr.payment_account, loan.payment_account
	).set(lr.loan_account, loan.loan_account).set(
		lr.penalty_income_account, loan.penalty_income_account
	).where(
		lr.docstatus < 2
	).run()
