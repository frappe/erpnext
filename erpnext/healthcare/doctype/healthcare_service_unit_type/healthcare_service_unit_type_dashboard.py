from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'service_unit_type',
		'transactions': [
			{
				'label': _('Healthcare Service Units'),
				'items': ['Healthcare Service Unit']
			},
		]
	}
