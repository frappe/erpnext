from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'payroll_entry',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
		},
		'transactions': [
			{
				'items': ['Salary Slip', 'Journal Entry']
			}
		]
	}