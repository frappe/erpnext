from frappe import _

def get_data():
	return {
		'fieldname': 'service_level',
		'transactions': [
			{
				'label': _('Service Level Agreement'),
				'items': ['Service Level Agreement']
			}
		]
	}