from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_registration_order',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Journal Entry', 'Payment Entry']
			},
			{
				'label': _('Reference'),
				'items': ['Vehicle Invoice Movement', 'Vehicle Registration Receipt']
			},
		]
	}
