from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname':  'leave_policy',
		'transactions': [
			{
				'label': _('Leaves'),
				'items': ['Leave Policy Assignment', 'Leave Allocation']
			},
		]
	}