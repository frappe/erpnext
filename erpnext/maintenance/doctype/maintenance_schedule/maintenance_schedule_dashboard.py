from frappe import _

def get_data():
	return {
		'fieldname': 'maintenance_schedule',
		'non_standard_fieldnames': {
			'Maintenance Visit': 'prevdoc_docname',
		},
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Maintenance Visit', 'Opportunity']
			},
		]
	}
