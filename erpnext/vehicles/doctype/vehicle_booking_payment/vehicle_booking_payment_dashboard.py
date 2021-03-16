from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_booking_payment',
		'transactions': [
			{
				'label': _('Deposit'),
				'items': ['Vehicle Booking Payment']
			},
		]
	}
