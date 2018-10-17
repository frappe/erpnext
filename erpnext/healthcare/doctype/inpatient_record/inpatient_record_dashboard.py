from frappe import _

def get_data():
	return {
		'fieldname': 'inpatient_record',
		'transactions': [
			{
				'label': _('Appointments and Encounters'),
				'items': ['Patient Appointment', 'Patient Encounter']
			},
			{
				'label': _('Lab Tests and Vital Signs'),
 				'items': ['Lab Test', 'Clinical Procedure', 'Sample Collection', 'Vital Signs']
			}
		]
	}
