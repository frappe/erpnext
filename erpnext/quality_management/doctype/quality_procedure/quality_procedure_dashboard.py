from frappe import _

def get_data():
	return {
		'fieldname': 'procedure',
		'transactions': [
			{
				'label': _('Goal'),
				'items': ['Quality Goal']
			},
		],
	}