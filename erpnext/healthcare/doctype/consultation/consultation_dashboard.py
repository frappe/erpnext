from frappe import _

def get_data():
	return {
		'fieldname': 'consultation',
		'non_standard_fieldnames': {
			'Patient Medical Record': 'reference_name'
		},
		'transactions': [
			{
				'label': _('Records'),
				'items': ['Vital Signs', 'Patient Medical Record']
			},
		]
	}
