from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'issue',
		'transactions': [
			{
				'label': _('Activity'),
				'items': ['Task']
			}
		]
	}
