from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the Time Sheets created against this project'),
		'fieldname': 'project_update',
		'transactions': [
			{
				'label': _('Project'),
				'items': ['Project']
			},

		]
	}
