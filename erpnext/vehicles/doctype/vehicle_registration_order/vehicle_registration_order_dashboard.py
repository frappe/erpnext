from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_registration_order',
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Journal Entry', 'Payment Entry']
			},
			{
				'label': _('Reference'),
				'items': ['Vehicle Invoice Movement']
			},
		]
	}
