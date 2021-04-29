from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'encounter',
		'non_standard_fieldnames': {
			'Patient Medical Record': 'reference_name',
			'Inpatient Medication Order': 'patient_encounter',
			'Healthcare Service Order': 'order_group'
		},
		'transactions': [
			{
				'label': _('Records'),
				'items': ['Vital Signs', 'Patient Medical Record']
			},
			{
				'label': _('Orders'),
				'items': ['Inpatient Medication Order', 'Healthcare Service Order']
			}
		],
		'disable_create_buttons': ['Inpatient Medication Order']
	}
