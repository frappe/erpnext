from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'bank_transaction',
		'transactions': [
			{
				'label': _('Accounting Entry'),
				'items': ['Bank Transaction Accounting Entry']
			}
		]
	}