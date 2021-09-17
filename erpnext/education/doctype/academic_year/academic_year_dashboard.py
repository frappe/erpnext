from __future__ import unicode_literals

from frappe import _


def get_data():
	return {
		'fieldname': 'academic_year',
		'transactions': [
			{
				'label': _('Student'),
				'items': ['Student Admission', 'Student Applicant', 'Student Group', 'Student Log']
			},
			{
				'label': _('Fee'),
				'items': ['Fees', 'Fee Schedule', 'Fee Structure']
			},
			{
				'label': _('Academic Term and Program'),
				'items': ['Academic Term', 'Program Enrollment']
			},
			{
				'label': _('Assessment'),
				'items': ['Assessment Plan', 'Assessment Result']
			}
		]
	}
