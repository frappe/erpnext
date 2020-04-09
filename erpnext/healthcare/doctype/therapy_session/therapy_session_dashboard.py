from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'therapy_session',
		'transactions': [
			{
				'label': _('Evaluations'),
				'items': ['Motor Assessment Scale']
			}
		]
	}
