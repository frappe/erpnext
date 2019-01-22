from frappe import _

def get_data():
	return {
		'fieldname': 'work_order',
		'transactions': [
			{
				'items': ['Stock Entry', 'Job Card']
			}
		]
	}