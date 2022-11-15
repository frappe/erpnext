from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_booking_order',
		'non_standard_fieldnames': {
			'Payment Request': 'reference_name',
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Vehicle Booking Payment', 'Journal Entry', 'Payment Entry']
			},
			{
				'label': _('Delivery'),
				'items': ['Vehicle Receipt', 'Vehicle Delivery', 'Project']
			},
			{
				'label': _('Invoice'),
				'items': ['Vehicle Invoice', 'Vehicle Invoice Movement', 'Vehicle Invoice Delivery']
			},
			{
				'label': _('Registration'),
				'items': ['Vehicle Registration Order', 'Vehicle Registration Receipt', 'Vehicle Transfer Letter']
			}
		]
	}
