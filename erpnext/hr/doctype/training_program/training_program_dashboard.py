from frappe import _

def get_data():
	return {
		'fieldname': 'training_program',
		'transactions': [
			{
				'label': _('Training Events'),
				'items': ['Training Event']
			},
		]
	}