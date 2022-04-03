import frappe


def execute():
	frappe.reload_doc("hr", "doctype", "salary_slip_loan")

	loans = frappe.db.get_all("Loan", {'docstatus': ['>', 0]})
	for d in loans:
		doc = frappe.get_doc("Loan", d.name)
		doc.update_total_amount_paid(update_modified=False)
		doc.set_status(update=True, update_modified=False)

	salary_slip_loan = frappe.db.sql("""
		select sl.name as salary_slip_loan, sl.loan, ss.start_date, ss.end_date, ss.employee
		from `tabSalary Slip Loan` sl
		inner join `tabSalary Slip` ss on ss.name = sl.parent
		where ss.docstatus = 1 and ifnull(sl.loan_repayment_detail, '') = ''
	""", as_dict=1)

	for ssl in salary_slip_loan:
		loan_details = get_loan_details(ssl.start_date, ssl.end_date, ssl.employee, ssl.loan)
		if len(loan_details) == 1:
			loan_details = loan_details[0]
			frappe.db.set_value("Salary Slip Loan", ssl.salary_slip_loan, {
				'loan_repayment_detail': loan_details.loan_repayment_detail,
				'loan_repayment_date': loan_details.payment_date,
			}, None, update_modified=False)


def get_loan_details(start_date, end_date, employee, loan):
	return frappe.db.sql("""
		select loan.name, rps.name as loan_repayment_detail,
			rps.principal_amount, rps.interest_amount, rps.total_payment,
			rps.payment_date,
			loan.loan_account, loan.interest_income_account
		from
			`tabRepayment Schedule` as rps, `tabLoan` as loan
		where
			loan.name = rps.parent
			and loan.docstatus = 1
			and rps.payment_date between %s and %s
			and rps.paid = 1
			and loan.repay_from_salary = 1
			and loan.applicant_type = 'Employee' and loan.applicant = %s
			and loan.name = %s
	""", (start_date, end_date, employee, loan), as_dict=True) or []
