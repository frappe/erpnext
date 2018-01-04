from frappe import _

def get_data():
	return {
		'fieldname': 'lead',
		'transactions': [
			{
				'items': ['Opportunity', 'Quotation']
			},
		]
	}