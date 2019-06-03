from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the attendance of this Employee'),
		'fieldname': 'employee',
		'transactions': [
			{
				'label': _('Leave and Attendance'),
				'items': ['Attendance', 'Attendance Request', 'Leave Application', 'Leave Allocation']
			},
			{
				'label': _('Payroll'),
				'items': ['Salary Structure Assignment', 'Salary Slip', 'Additional Salary', 'Timesheet']
			},
			{
				'label': _('Shift'),
				'items': ['Shift Request', 'Shift Assignment']
			},
			{
				'label': _('Expense'),
				'items': ['Expense Claim', 'Travel Request']
			},
			{
				'label': _('Evaluation'),
				'items': ['Appraisal']
			},
			{
				'label': _('Lifecycle'),
				'items': ['Employee Transfer', 'Employee Promotion', 'Employee Separation']
			},
			{
				'label': _('Benefit'),
				'items': ['Employee Incentive', 'Retention Bonus','Employee Benefit Application', 'Employee Benefit Claim']
			},
			{
				'label': _('Training'),
				'items': ['Training Event', 'Training Result', 'Training Feedback', 'Employee Skill Map']
			},
		]
	}