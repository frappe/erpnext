from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_allocation',
		'transactions': [
			{
				'label': _('Order'),
				'items': ['Vehicle Booking Order']
			}
		]
	}
