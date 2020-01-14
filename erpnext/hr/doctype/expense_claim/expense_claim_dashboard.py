from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
        'fieldname': 'reference_name',
		'internal_links': {
			'Employee Advance': ['advances', 'employee_advance']
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Journal Entry']
			},
			{
				'label': _('Reference'),
				'items': ['Employee Advance']
			},
		]
	}