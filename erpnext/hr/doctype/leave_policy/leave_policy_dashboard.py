from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname':  'leave_policy',
		'non_standard_fieldnames': {
			'Employee Grade': 'default_leave_policy'
		},
		'transactions': [
			{
				'label': _('Employees'),
				'items': ['Employee', 'Employee Grade']
			},
			{
				'label': _('Leaves'),
				'items': ['Leave Allocation']
			},
		]
	}	
