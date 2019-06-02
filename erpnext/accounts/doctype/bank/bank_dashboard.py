from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'bank',
		'transactions': [
			{
				'label': _('Bank Deatils'),
				'items': ['Bank Account', 'Bank Statement Transaction Entry', 'Bank Guarantee']
			},
			{
				'items': ['Payment Order']
			}
		]
	}
