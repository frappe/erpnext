from frappe import _

data = {
	'heatmap': True,
	'heatmap_message': _('This is based on the attendance of this Student'),
	'fieldname': 'student',
	'transactions': [
		{
			'items': ['Student Group', 'Student Attendance', 'Program Enrollment' ]
		},
		{
			'items': ['Fees', 'Examination']
		}
	]
}