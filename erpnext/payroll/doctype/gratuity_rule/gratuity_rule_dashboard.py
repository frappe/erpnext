from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'gratuity_rule',
		'transactions': [
			{
				'label': _('Gratuity'),
				'items': ['Gratuity']
			}
		]
	}
