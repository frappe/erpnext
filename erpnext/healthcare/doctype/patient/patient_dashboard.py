from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Patient. See timeline below for details'),
		'fieldname': 'patient',
		'transactions': [
			{
				'label': _('Appointments and Consultations'),
				'items': ['Appointment', 'Consultation', 'Procedure Appointment']
			},
			{
				'label': _('Test and Procedures'),
				'items': ['Lab Test', 'Procedure']
			}
		]
	}
