from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'reference_docname',
		'transactions': [
			{
				'label': _('Task'),
				'items': ['Task']
			}
		]
	}
