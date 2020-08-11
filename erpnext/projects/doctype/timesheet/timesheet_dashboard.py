from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'time_sheet',
		'transactions': [
			{
				'label': _('References'),
				'items': ['Sales Invoice', 'Salary Slip']
			}
		]
	}