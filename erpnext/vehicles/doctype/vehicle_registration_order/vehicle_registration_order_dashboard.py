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
				'label': _('Accounting'),
				'items': ['Journal Entry', 'Payment Entry']
			},
			{
				'label': _('Registration'),
				'items': ['Vehicle Registration Receipt', 'Vehicle Transfer Letter']
			},
			{
				'label': _('Vehicle Invoice'),
				'items': ['Vehicle Invoice Movement', 'Vehicle Invoice Delivery']
			},
			{
				'label': _('Registration Invoice'),
				'items': ['Sales Invoice']
			},
		]
	}
