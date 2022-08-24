from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'bank_transaction',
		'transactions': [
			{
				'label': _('Journal Entry'),
				'items': ['Journal Entry', 'Print Bank Check']
			}
		]
	}