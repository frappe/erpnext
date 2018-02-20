from frappe import _

def get_data():
	return {
		'fieldname': 'production_plan',
		'transactions': [
			{
				'label': _('Related'),
				'items': ['Production Order', 'Material Request']
			},
		]
	}