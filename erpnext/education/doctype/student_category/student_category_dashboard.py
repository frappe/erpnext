from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'student_category',
		'transactions': [
			{
				'label': _('Fee'),
				'items': ['Fee Structure', 'Fee Schedule', 'Fees']
			}
		]
	}
