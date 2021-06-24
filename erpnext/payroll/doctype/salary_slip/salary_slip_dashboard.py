from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'salary_slip',
		'transactions': [
			{
				'items': [_('Overtime Slip')]
			}
		]
	}