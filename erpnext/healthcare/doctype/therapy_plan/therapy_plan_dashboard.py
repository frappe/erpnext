from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'therapy_plan',
		'transactions': [
			{
				'label': _('Therapy Sessions'),
				'items': ['Therapy Session']
			}
		]
	}
