from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'template',
		'transactions': [
			{
				'label': _('Lab Tests'),
				'items': ['Lab Test']
			}
		]
	}
