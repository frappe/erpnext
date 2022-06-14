from __future__ import unicode_literals
from frappe import _


def get_data():
	return {
		'fieldname': 'brand',
		'transactions': [
			{
				'label': _('Configuration'),
				'items': ['Item Default Rule']
			}
		]
	}
