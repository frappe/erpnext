from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'loyalty_program',
		'transactions': [
			{
				'items': ['Sales Invoice', 'Customer']
			}
		]
	}
