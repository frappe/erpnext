from frappe import _


def get_data():
	return {
		'fieldname':  'attendance_request',
		'transactions': [
			{
				'label': _('Attendance'),
				'items': ['Attendance']
			}
		]
	}
