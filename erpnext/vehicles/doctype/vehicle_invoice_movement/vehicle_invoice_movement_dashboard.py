from frappe import _

def get_data():
	return {
		'fieldname': 'vehicle_invoice_movement',
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Vehicle Invoice']
			}
		]
	}
