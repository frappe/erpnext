from frappe import _

def get_data():
	return {
		'fieldname': 'shift',
		'non_standard_fieldnames': {
			'Employee': 'default_shift',
			'Shift Request': 'shift_type',
			'Shift Assignment': 'shift_type'
		},
		'transactions': [
			{
				'label': _("Assignment"),
				'items': ['Employee', 'Shift Request', 'Shift Assignment']
			},
			{
				'label': _("Attendance"),
				'items': ['Attendance', 'Employee Checkin']
			}
		]
	}
