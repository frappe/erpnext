from frappe import _

def get_data():
	return {
		'fieldname': 'appointment',
		'non_standard_fieldnames': {
			'Patient Medical Record': 'reference_name'
		},
		'transactions': [
			{
				'label': _('Consultations'),
				'items': ['Patient Encounter', 'Vital Signs', 'Patient Medical Record']
			}
		]
	}
