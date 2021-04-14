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
				'items': ['Vehicle Booking Payment']
			},
			{
				'label': _('Delivery'),
				'items': ['Vehicle Receipt', 'Vehicle Delivery']
			},
			{
				'label': _('Invoice'),
				'items': ['Vehicle Invoice Receipt', 'Vehicle Invoice Delivery']
			},
			{
				'label': _('Transfer'),
				'items': ['Vehicle Transfer Letter']
			}
		]
	}
