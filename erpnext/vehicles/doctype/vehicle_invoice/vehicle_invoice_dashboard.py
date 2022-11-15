from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_invoice',
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Vehicle Invoice Movement', 'Vehicle Invoice Delivery']
			}
		]
	}
