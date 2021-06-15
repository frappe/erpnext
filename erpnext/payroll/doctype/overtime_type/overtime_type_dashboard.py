from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'overtime_type',
		'transactions': [
			{
				'items': ['Attendance', 'Timesheet']
			},
			{
				'items': ['Overtime Slip']
			}
		]
	}