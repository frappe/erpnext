from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'work_order',
		'non_standard_fieldnames': {
			'Batch': 'reference_name'
		},
		'transactions': [
			{
				'label': _('Transactions'),
				'items': ['Stock Entry', 'Job Card', 'Pick List']
			},
			{
				'label': _('Reference'),
				'items': ['Serial No', 'Batch']
			}
		]
	}