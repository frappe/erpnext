from frappe import _

def get_data():
	return {
		'fieldname': 'project_template',
		'transactions': [
			{
				'label': _("Project"),
				'items': ['Project']
			}
		]
	}
