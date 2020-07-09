from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'academic_term',
		'transactions': [
			{
				'label': _('Student'),
				'items': ['Student Applicant', 'Student Group', 'Student Log']
			},
			{
				'label': _('Fee'),
				'items': ['Fees', 'Fee Schedule', 'Fee Structure']
			},
			{
				'label': _('Program'),
				'items': ['Program Enrollment']
			},
			{
				'label': _('Assessment'),
				'items': ['Assessment Plan', 'Assessment Result']
			}
		]
	}