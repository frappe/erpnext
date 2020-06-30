from __future__ import unicode_literals

def get_data():
	return {
		'fieldname':  'leave_policy',
		'non_standard_fieldnames': {
			'Employee Grade': 'default_leave_policy'
		},
		'transactions': [
			{
				'label': ('Employees'),
				'items': ['Employee', 'Employee Grade']
			},
			{
				'label': ('Leaves'),
				'items': ['Leave Allocation']
			},
		]
	}




	