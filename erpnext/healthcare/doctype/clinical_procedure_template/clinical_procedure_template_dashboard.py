from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'procedure_template',
		'transactions': [
			{
				'label': _('Consultations'),
				'items': ['Clinical Procedure']
			}
		]
	}
