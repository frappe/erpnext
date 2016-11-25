from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the attendance of this Employee'),
		'fieldname': 'employee',
		'transactions': [
			{
				'label': _('Leave and Attendance'),
				'items': ['Attendance', 'Leave Application', 'Leave Allocation']
			},
			{
				'label': _('Payroll'),
				'items': ['Salary Structure', 'Salary Slip', 'Timesheet']
			},
			{
				'label': _('Expense'),
				'items': ['Expense Claim']
			},
			{
				'label': _('Evaluation'),
				'items': ['Appraisal']
			}
		]
	}