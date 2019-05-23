from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'loyalty_program',
		'transactions': [
			{
				'label': _('Sales Invoice'),
				'items': ['Sales Invoice']
			},
			{
				'label': _('Customers'),
				'items': ['Customer']
			}
		]
	}
