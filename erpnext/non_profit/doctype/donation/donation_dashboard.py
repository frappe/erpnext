from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'donation',
		'non_standard_fieldnames': {
			'Payment Entry': 'reference_name'
		},
		'internal_links': {
			'Sales Order': ['items', 'sales_order']
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry']
			}
		]
	}