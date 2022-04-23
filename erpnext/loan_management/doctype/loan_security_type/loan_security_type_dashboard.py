from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'loan_security_type',
		'transactions': [
			{
				'items': ['Loan Security', 'Loan Security Price']
			},
			{
				'items': ['Loan Security Pledge', 'Loan Security Unpledge']
			}
		]
	}