from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the attendance of this Employee'),
		'fieldname': 'employee',
		'non_standard_fieldnames': {
			'Bank Account': 'party'
		},
		'transactions': [
			{
				'label': _('Leave and Attendance'),
				'items': ['Attendance', 'Attendance Request', 'Leave Application', 'Leave Allocation', 'Employee Checkin']
			},
			{
				'label': _('Lifecycle'),
				'items': ['Employee Transfer', 'Employee Promotion', 'Employee Separation']
			},
			{
				'label': _('Shift'),
				'items': ['Shift Request', 'Shift Assignment']
			},
			{
				'label': _('Expense'),
				'items': ['Expense Claim', 'Travel Request', 'Employee Advance']
			},
			{
				'label': _('Benefit'),
				'items': ['Employee Benefit Application', 'Employee Benefit Claim']
			},
			{
				'label': _('Evaluation'),
				'items': ['Appraisal']
			},
			{
				'label': _('Payroll'),
				'items': ['Salary Structure Assignment', 'Salary Slip', 'Additional Salary', 'Timesheet','Employee Incentive', 'Retention Bonus', 'Bank Account']
			},
			{
				'label': _('Training'),
				'items': ['Training Event', 'Training Result', 'Training Feedback', 'Employee Skill Map']
			},
		]
	}
