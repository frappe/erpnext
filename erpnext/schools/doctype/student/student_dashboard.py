from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the attendance of this Student'),
		'fieldname': 'student',
		'transactions': [
			{
				'label': _('Admission'),
				'items': ['Program Enrollment']
			},
			{
				'label': _('Fee'),
				'items': ['Fees']
			},
			{
				'label': _('Assessment'),
				'items': ['Assessment Result']
			},
			{
				'label': _('Student Activity'),
				'items': ['Student Log', 'Student Group', 'Student Attendance', 'Student Leave Application']
			}
		]
	}