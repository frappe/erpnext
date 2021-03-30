from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'loan',
		'non_standard_fieldnames': {
			'Loan Disbursement': 'against_loan',
			'Loan Repayment': 'against_loan',
		},
		'transactions': [
			{
				'items': ['Loan Security Pledge', 'Loan Security Shortfall', 'Loan Disbursement']
			},
			{
				'items': ['Loan Repayment', 'Loan Interest Accrual', 'Loan Write Off', 'Loan Security Unpledge']
			}
		]
	}