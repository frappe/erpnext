from __future__ import unicode_literals

def get_data():
	return {
		'fieldname':  'leave_policy',
		'non_standard_fieldnames': {
			'Employee Grade': 'default_leave_policy'
		},
		'transactions': [
			{
				'items': ['Employee']
			},
			{
				'items': ['Employee Grade']
			}
		]
	}