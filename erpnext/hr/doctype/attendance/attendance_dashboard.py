from frappe import _

def get_data():
	return {
		'fieldname': 'attendance',
		'transactions': [
			{
				'label': _('Checkins'),
				'items': ['Employee Checkin']
			}
		]
	}
