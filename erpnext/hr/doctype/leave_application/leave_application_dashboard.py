from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'leave_application',
		'transactions': [
			{
				'items': ['Attendance']
			}
		],
        'reports': [
			{
                'label': _('Reports'),
				'items': ['Employee Leave Balance']
			}
		]
    }