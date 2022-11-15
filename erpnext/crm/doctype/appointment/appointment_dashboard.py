from frappe import _

def get_data():
	return {
		'fieldname': 'appointment',
		'non_standard_fieldnames': {
			'Appointment': 'previous_appointment',
		},
		'transactions': [
			{
				'label': _('Rescheduled By'),
				'items': ['Appointment']
			},
			{
				'label': _('Project'),
				'items': ['Project']
			},
		]
	}
