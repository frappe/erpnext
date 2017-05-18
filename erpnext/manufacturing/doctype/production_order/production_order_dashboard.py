from frappe import _

def get_data():
	return {
		'fieldname': 'production_order',
		'transactions': [
			{
				'items': ['Stock Entry', 'Timesheet']
			}
		]
	}