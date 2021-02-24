from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_booking_order',
		'non_standard_fieldnames': {
			'Journal Entry': 'original_reference_name',
			'Payment Entry': 'original_reference_name',
			'Payment Request': 'reference_name',
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Vehicle Booking Payment', 'Payment Request']
			},
			{
				'label': _('Delivery'),
				'items': ['Purchase Receipt', 'Delivery Note']
			},
			{
				'label': _('Invoice'),
				'items': ['Purchase Invoice', 'Sales Invoice']
			},
		]
	}
