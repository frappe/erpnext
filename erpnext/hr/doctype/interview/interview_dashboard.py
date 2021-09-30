from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'interview',
		'transactions': [
			{
				'label': _('Feedback'),
				'items': ['Interview Feedback']
			},
		]
	}