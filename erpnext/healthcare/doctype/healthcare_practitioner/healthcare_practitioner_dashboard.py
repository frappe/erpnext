from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Healthcare Practitioner.'),
		'fieldname': 'practitioner',
		'non_standard_fieldnames': {
			'Inpatient Record': 'primary_practitioner'
		},
		'transactions': [
			{
				'label': _('Inpatient'),
				'items': ['Inpatient Record', 'Inpatient Medication Order']
			}
		]
	}
