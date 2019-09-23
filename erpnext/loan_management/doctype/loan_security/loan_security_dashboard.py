from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'loan_security',
		'transactions': [
			{
				'items': ['Loan Application']
			},
			{
				'items': ['Loan Security Price']
			},
			{
				'items': ['Loan Security Pledge']
			},
			{
				'items': ['Loan Security Unpledge']
			}
		]
	}