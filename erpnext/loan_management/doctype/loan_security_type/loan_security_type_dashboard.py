from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'loan_security_type',
		'transactions': [
			{
				'items': ['Loan Security']
			},
			{
				'items': ['Process Loan Security']
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