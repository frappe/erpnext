from frappe import _

def get_data():
	return {
		'fieldname': 'payment_order',
		'transactions': [
			{
				'items': ['Payment Entry', 'Journal Entry']
			}
		]
	}