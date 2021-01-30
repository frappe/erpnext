from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'encounter',
		'non_standard_fieldnames': {
			'Inpatient Medication Order': 'patient_encounter'
		},
		'transactions': [
			{
				'label': _('References'),
				'items': ['Inpatient Medication Order']
			}
		],
		'disable_create_buttons': ['Inpatient Medication Order']
	}
