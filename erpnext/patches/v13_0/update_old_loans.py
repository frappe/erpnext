from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import process_loan_interest_accrual_for_term_loans
from erpnext.loan_management.doctype.loan.loan import make_repayment_entry
from frappe.model.naming import make_autoname

def execute():

	# Create a penalty account for loan types

	frappe.reload_doc('loan_management', 'doctype', 'loan_type')
	frappe.reload_doc('loan_management', 'doctype', 'loan')
	frappe.reload_doc('loan_management', 'doctype', 'repayment_schedule')
	frappe.reload_doc('loan_management', 'doctype', 'process_loan_interest_accrual')
	frappe.reload_doc('loan_management', 'doctype', 'loan_repayment')
	frappe.reload_doc('loan_management', 'doctype', 'loan_repayment_detail')
	frappe.reload_doc('loan_management', 'doctype', 'loan_interest_accrual')
	frappe.reload_doc('accounts', 'doctype', 'gl_entry')
	frappe.reload_doc('accounts', 'doctype', 'journal_entry_account')

	updated_loan_types = []

	loans = frappe.get_all('Loan', fields=['name', 'loan_type', 'company', 'status', 'mode_of_payment',
		'applicant_type', 'applicant', 'loan_account', 'payment_account', 'interest_income_account'],
		filters={'docstatus': 1})

	for loan in loans:
		# Update details in Loan Types and Loan
		loan_type_company = frappe.db.get_value('Loan Type', loan.loan_type, 'company')
		loan_type = loan.loan_type

		group_income_account = frappe.get_value('Account', {'company': loan.company,
			'is_group': 1, 'root_type': 'Income', 'account_name': _('Indirect Income')})

		if not group_income_account:
			group_income_account = frappe.get_value('Account', {'company': loan.company,
				'is_group': 1, 'root_type': 'Income'})

		penalty_account = create_account(company=loan.company, account_type='Income Account',
			account_name='Penalty Account', parent_account=group_income_account)

		# Same loan type used for multiple companies
		if loan_type_company and loan_type_company != loan.company:
			# get loan type for appropriate company
			loan_type_name = frappe.get_value('Loan Type', {'company': loan.company,
				'mode_of_payment': loan.mode_of_payment, 'loan_account': loan.loan_account,
				'payment_account': loan.payment_account, 'interest_income_account': loan.interest_income_account,
				'penalty_income_account': loan.penalty_income_account}, 'name')

			if not loan_type_name:
				loan_type_name = create_loan_type(loan, loan_type_name, penalty_account)

			# update loan type in loan
			frappe.db.sql("UPDATE `tabLoan` set loan_type = %s where name = %s", (loan_type_name,
				loan.name))

			loan_type = loan_type_name
			if loan_type_name not in updated_loan_types:
				updated_loan_types.append(loan_type_name)

		elif not loan_type_company:
			loan_type_doc = frappe.get_doc('Loan Type', loan.loan_type)
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
			if loan.status == 'Fully Disbursed':
				status = 'Disbursed'
			elif loan.status == 'Repaid/Closed':
				status = 'Closed'
			else:
				status = loan.status

			frappe.db.set_value('Loan', loan.name, {
				'is_term_loan': 1,
				'penalty_income_account': penalty_account,
				'status': status
			})

			process_loan_interest_accrual_for_term_loans(posting_date=nowdate(), loan_type=loan_type,
				loan=loan.name)

			payments = frappe.db.sql(''' SELECT j.name, a.debit, a.debit_in_account_currency, j.posting_date
				FROM `tabJournal Entry` j, `tabJournal Entry Account` a
				WHERE a.parent = j.name and a.reference_type='Loan' and a.reference_name = %s
				and a.account = %s and j.docstatus = 1
			''', (loan.name, loan.loan_account), as_dict=1)

			for payment in payments:
				repayment_entry = make_repayment_entry(loan.name, loan.loan_applicant_type, loan.applicant,
					loan_type, loan.company)

				repayment_entry.amount_paid = payment.debit_in_account_currency
				repayment_entry.posting_date = payment.posting_date
				repayment_entry.save()
				repayment_entry.submit()

				jv = frappe.get_doc('Journal Entry', payment.name)
				jv.flags.ignore_links = True
				jv.cancel()

def create_loan_type(loan, loan_type_name, penalty_account):
	loan_type_doc = frappe.new_doc('Loan Type')
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
