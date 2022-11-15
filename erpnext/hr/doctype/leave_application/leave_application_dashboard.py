
from frappe import _


def get_data():
	return {
		'fieldname': 'leave_application',
		'transactions': [
			{
				'label': _('Attendance'),
				'items': ['Attendance']
			}
		],
		# 'reports': [
		# 	{
		# 		'label': _('Reports'),
		# 		'items': ['Employee Leave Balance']
		# 	}
		# ]
    }