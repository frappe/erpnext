from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'leave_allocation',
        'transactions': [
            {
                'items': ['Compensatory Leave Request']
            },
            {
                'items': ['Leave Encashment']
            }
        ],
        'reports': [
			{
				'items': ['Employee Leave Balance']
			}
		]
    }