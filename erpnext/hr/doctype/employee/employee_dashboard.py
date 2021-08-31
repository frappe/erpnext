from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on the attendance of this Employee'),
		'fieldname': 'employee',
		'non_standard_fieldnames': {
			'Bank Account': 'party',
			'Employee Grievance': 'raised_by'
		},
		'transactions': [
			{
				'label': _('Attendance'),
				'items': ['Attendance', 'Attendance Request', 'Employee Checkin']
			},
			{
				'label': _('Leave'),
				'items': ['Leave Application', 'Leave Allocation', 'Leave Policy Assignment']
			},
			{
				'label': _('Lifecycle'),
				'items': ['Employee Transfer', 'Employee Promotion', 'Employee Separation', 'Employee Grievance']
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
				'label': _('Payroll'),
				'items': ['Salary Structure Assignment', 'Salary Slip', 'Additional Salary', 'Timesheet','Employee Incentive', 'Retention Bonus', 'Bank Account']
			},
			{
				'label': _('Training'),
				'items': ['Training Event', 'Training Result', 'Training Feedback', 'Employee Skill Map']
			},
			{
				'label': _('Evaluation'),
				'items': ['Appraisal']
			},
		]
	}
