from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual import process_loan_interest_accrual_for_term_loans
from erpnext.loan_management.doctype.loan.loan import make_repayment_entry

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

	updated_loan_types = []

	loans = frappe.get_all('Loan', fields=['name', 'loan_type', 'company', 'status', 'mode_of_payment',
		'applicant_type', 'applicant', 'loan_account', 'payment_account', 'interest_income_account'])

	for loan in loans:
		# Update details in Loan Types and Loan
		loan_type_company = frappe.db.get_value('Loan Type', loan.loan_type, 'company')

		group_income_account = frappe.get_value('Account', {'company': loan.company,
			'is_group': 1, 'root_type': 'Income', 'account_name': _('Indirect Income')})

		if not group_income_account:
			group_income_account = frappe.get_value('Account', {'company': loan.company,
				'is_group': 1, 'root_type': 'Income'})

		penalty_account = create_account(company=loan.company, account_type='Income Account',
			account_name='Penalty Account', parent_account=group_income_account)

		if not loan_type_company:
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

		if loan.loan_type in updated_loan_types:
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

			process_loan_interest_accrual_for_term_loans(posting_date=nowdate(), loan_type=loan.loan_type,
				loan=loan.name)

			payments = frappe.db.sql(''' SELECT j.name, a.debit, a.debit_in_account_currency, j.posting_date
				FROM `tabJournal Entry` j, `tabJournal Entry Account` a
				WHERE a.parent = j.name and a.reference_type='Loan' and a.reference_name = %s
				and account = %s
			''', (loan.name, loan.loan_account), as_dict=1)

			for payment in payments:
				repayment_entry = make_repayment_entry(loan.name, loan.loan_applicant_type, loan.applicant,
					loan.loan_type, loan.company)

				repayment_entry.amount_paid = payment.debit_in_account_currency
				repayment_entry.posting_date = payment.posting_date
				repayment_entry.save()
				repayment_entry.submit()

				jv = frappe.get_doc('Journal Entry', payment.name)
				jv.flags.ignore_links = True
				jv.cancel()

