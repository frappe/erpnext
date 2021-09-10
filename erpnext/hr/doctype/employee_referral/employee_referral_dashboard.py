from __future__ import unicode_literals


def get_data():
	return {
		'fieldname': 'employee_referral',
		'non_standard_fieldnames': {
			'Additional Salary': 'ref_docname'
		},
		'transactions': [
			{
				'items': ['Job Applicant', 'Additional Salary']
			},

		]
	}
