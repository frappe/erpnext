from frappe import _


def get_data():
	return {
		'fieldname': 'program',
		'transactions': [
			{
				'label': _('Admission and Enrollment'),
				'items': ['Student Applicant', 'Program Enrollment']
			},
			{
				'label': _('Student Activity'),
				'items': ['Student Group', 'Student Log']
			},
			{
				'label': _('Fee'),
				'items': ['Fees','Fee Structure', 'Fee Schedule']
			},
			{
				'label': _('Assessment'),
				'items': ['Assessment Plan', 'Assessment Result']
			}
		]
	}
