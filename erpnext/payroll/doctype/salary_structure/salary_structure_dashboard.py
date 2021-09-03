from __future__ import unicode_literals


def get_data():
	return {
		'fieldname': 'salary_structure',
		'non_standard_fieldnames': {
			'Employee Grade': 'default_salary_structure'
		},
		'transactions': [
			{
				'items': ['Salary Structure Assignment', 'Salary Slip']
			},
			{
				'items': ['Employee Grade']
			},
		]
	}
