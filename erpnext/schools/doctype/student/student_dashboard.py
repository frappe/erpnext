from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the attendance of this Student'),
		'fieldname': 'student',
		'transactions': [
			{
				'items': ['Student Log', 'Student Group', 'Student Attendance']
			},
			{
				'items': ['Program Enrollment', 'Fees', 'Assessment', 'Guardian']
			}
		]
	}