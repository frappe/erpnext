from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'program_enrollment',
		'transactions': [
			{
				'label': _('Course and Fee'),
				'items': ['Course Enrollment', 'Fees']
			}
		],
		'reports': [
			{
				'label': _('Report'),
				'items': ['Student and Guardian Contact Details']
			}
		]
	}
