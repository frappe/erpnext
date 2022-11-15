from frappe import _

def get_data():
	return {
		'fieldname': 'project_workshop',
		'transactions': [
			{
				'label': _('Project'),
				'items': ['Project']
			},
			{
				'label': _('Vehicle Movement'),
				'items': ['Vehicle Service Receipt', 'Vehicle Gate Pass']
			},
		]
	}
