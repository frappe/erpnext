from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'reference_name',
		'non_standard_fieldnames': {
			'Additional Salary': 'ref_docname',
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry']
			},
			{
				'label': _('Additional Salary'),
				'items': ['Additional Salary']
			}
		]
	}