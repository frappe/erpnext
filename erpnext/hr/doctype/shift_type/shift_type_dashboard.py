from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'shift',
		'non_standard_fieldnames': {
			'Shift Request': 'shift_type',
			'Shift Assignment': 'shift_type'
		},
		'transactions': [
			{
				'items': ['Attendance', 'Employee Checkin', 'Shift Request', 'Shift Assignment']
			}
		]
	}
