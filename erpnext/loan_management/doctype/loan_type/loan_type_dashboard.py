from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'loan_type',
		'transactions': [
			{
				'items': ['Loan Repayment', 'Loan']
			},
			{
				'items': ['Loan Application']
			}
		]
	}