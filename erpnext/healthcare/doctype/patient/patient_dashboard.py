from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Patient. See timeline below for details'),
		'fieldname': 'patient',
		'internal_links': {
			'Inpatient Medication Entry': ['medication_orders', 'patient']
		},
		'transactions': [
			{
				'label': _('Inpatient'),
				'items': ['Inpatient Record', 'Inpatient Medication Order', 'Inpatient Medication Entry']
			}
		]
	}
