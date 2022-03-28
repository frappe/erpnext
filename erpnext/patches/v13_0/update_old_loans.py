import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import flt, nowdate

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.loan_management.doctype.loan_repayment.loan_repayment import (
	get_accrued_interest_entries,
)
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
	process_loan_interest_accrual_for_term_loans,
)


def execute():

	# Create a penalty account for loan types

	frappe.reload_doc("loan_management", "doctype", "loan_type")
	frappe.reload_doc("loan_management", "doctype", "loan")
	frappe.reload_doc("loan_management", "doctype", "repayment_schedule")
	frappe.reload_doc("loan_management", "doctype", "process_loan_interest_accrual")
	frappe.reload_doc("loan_management", "doctype", "loan_repayment")
	frappe.reload_doc("loan_management", "doctype", "loan_repayment_detail")
	frappe.reload_doc("loan_management", "doctype", "loan_interest_accrual")
	frappe.reload_doc("accounts", "doctype", "gl_entry")
	frappe.reload_doc("accounts", "doctype", "journal_entry_account")

	updated_loan_types = []
	loans_to_close = []

	# Update old loan status as closed
	if frappe.db.has_column("Repayment Schedule", "paid"):
		loans_list = frappe.db.sql(
			"""SELECT distinct parent from `tabRepayment Schedule`
			where paid = 0 and docstatus = 1""",
			as_dict=1,
		)

		loans_to_close = [d.parent for d in loans_list]

	if loans_to_close:
		frappe.db.sql(
			"UPDATE `tabLoan` set status = 'Closed' where name not in (%s)"
			% (", ".join(["%s"] * len(loans_to_close))),
			tuple(loans_to_close),
		)

	loans = frappe.get_all(
		"Loan",
		fields=[
			"name",
			"loan_type",
			"company",
			"status",
			"mode_of_payment",
			"applicant_type",
			"applicant",
			"loan_account",
			"payment_account",
			"interest_income_account",
		],
		filters={"docstatus": 1, "status": ("!=", "Closed")},
	)

	for loan in loans:
		# Update details in Loan Types and Loan
		loan_type_company = frappe.db.get_value("Loan Type", loan.loan_type, "company")
		loan_type = loan.loan_type

		group_income_account = frappe.get_value(
			"Account",
			{
				"company": loan.company,
				"is_group": 1,
				"root_type": "Income",
				"account_name": _("Indirect Income"),
			},
		)

		if not group_income_account:
			group_income_account = frappe.get_value(
				"Account", {"company": loan.company, "is_group": 1, "root_type": "Income"}
			)

		penalty_account = create_account(
			company=loan.company,
			account_type="Income Account",
			account_name="Penalty Account",
			parent_account=group_income_account,
		)

		# Same loan type used for multiple companies
		if loan_type_company and loan_type_company != loan.company:
			# get loan type for appropriate company
			loan_type_name = frappe.get_value(
				"Loan Type",
				{
					"company": loan.company,
					"mode_of_payment": loan.mode_of_payment,
					"loan_account": loan.loan_account,
					"payment_account": loan.payment_account,
					"interest_income_account": loan.interest_income_account,
					"penalty_income_account": loan.penalty_income_account,
				},
				"name",
			)

			if not loan_type_name:
				loan_type_name = create_loan_type(loan, loan_type_name, penalty_account)

			# update loan type in loan
			frappe.db.sql(
				"UPDATE `tabLoan` set loan_type = %s where name = %s", (loan_type_name, loan.name)
			)

			loan_type = loan_type_name
			if loan_type_name not in updated_loan_types:
				updated_loan_types.append(loan_type_name)

		elif not loan_type_company:
			loan_type_doc = frappe.get_doc("Loan Type", loan.loan_type)
			loan_type_doc.is_term_loan = 1
			loan_type_doc.company = loan.company
			loan_type_doc.mode_of_payment = loan.mode_of_payment
			loan_type_doc.payment_account = loan.payment_account
			loan_type_doc.loan_account = loan.loan_account
			loan_type_doc.interest_income_account = loan.interest_income_account
			loan_type_doc.penalty_income_account = penalty_account
			loan_type_doc.submit()
			updated_loan_types.append(loan.loan_type)
			loan_type = loan.loan_type

		if loan_type in updated_loan_types:
			if loan.status == "Fully Disbursed":
				status = "Disbursed"
			elif loan.status == "Repaid/Closed":
				status = "Closed"
			else:
				status = loan.status

			frappe.db.set_value(
				"Loan",
				loan.name,
				{"is_term_loan": 1, "penalty_income_account": penalty_account, "status": status},
			)

			process_loan_interest_accrual_for_term_loans(
				posting_date=nowdate(), loan_type=loan_type, loan=loan.name
			)

			if frappe.db.has_column("Repayment Schedule", "paid"):
				total_principal, total_interest = frappe.db.get_value(
					"Repayment Schedule",
					{"paid": 1, "parent": loan.name},
					["sum(principal_amount) as total_principal", "sum(interest_amount) as total_interest"],
				)

				accrued_entries = get_accrued_interest_entries(loan.name)
				for entry in accrued_entries:
					interest_paid = 0
					principal_paid = 0

					if flt(total_interest) > flt(entry.interest_amount):
						interest_paid = flt(entry.interest_amount)
					else:
						interest_paid = flt(total_interest)

					if flt(total_principal) > flt(entry.payable_principal_amount):
						principal_paid = flt(entry.payable_principal_amount)
					else:
						principal_paid = flt(total_principal)

					frappe.db.sql(
						""" UPDATE `tabLoan Interest Accrual`
						SET paid_principal_amount = `paid_principal_amount` + %s,
							paid_interest_amount = `paid_interest_amount` + %s
						WHERE name = %s""",
						(principal_paid, interest_paid, entry.name),
					)

					total_principal = flt(total_principal) - principal_paid
					total_interest = flt(total_interest) - interest_paid


def create_loan_type(loan, loan_type_name, penalty_account):
	loan_type_doc = frappe.new_doc("Loan Type")
	loan_type_doc.loan_name = make_autoname("Loan Type-.####")
	loan_type_doc.is_term_loan = 1
	loan_type_doc.company = loan.company
	loan_type_doc.mode_of_payment = loan.mode_of_payment
	loan_type_doc.payment_account = loan.payment_account
	loan_type_doc.loan_account = loan.loan_account
	loan_type_doc.interest_income_account = loan.interest_income_account
	loan_type_doc.penalty_income_account = penalty_account
	loan_type_doc.submit()

	return loan_type_doc.name
