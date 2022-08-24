from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'dncxp',
		'transactions': [
			{
				'label': _('Payment Entry'),
				'items': ['Payment Entry']
			}
		]
	}