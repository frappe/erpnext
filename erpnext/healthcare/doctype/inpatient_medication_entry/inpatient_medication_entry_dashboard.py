from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'against_imoe',
		'internal_links': {
			'Inpatient Medication Order': ['medication_orders', 'against_imo']
		},
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Inpatient Medication Order']
			}
		]
	}
