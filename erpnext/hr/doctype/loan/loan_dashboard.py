from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'applicant',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Salary Slip': 'employee'
			},
		'transactions': [
			{
				'label': _('Applicant'),
				'items': ['Loan Application']
			},

			{
				'label': _('Account'),
				'items': ['Journal Entry']
			},
			{
				'label': _('Employee'),
				'items': ['Salary Slip']
			}
		]
	}