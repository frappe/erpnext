from frappe import _

links = {
	'fieldname': 'employee',
	'transactions': [
		{
			'label': _('Leave and Attendance'),
			'items': ['Attendance', 'Leave Application', 'Leave Allocation']
		},
		{
			'label': _('Payroll'),
			'items': ['Salary Structure', 'Salary Slip']
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