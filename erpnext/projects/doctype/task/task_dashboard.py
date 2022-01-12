from frappe import _


def get_data():
	return {
		'fieldname': 'task',
		'non_standard_fieldnames': {
			'Stock Entry': 'task_reference',
		},
		'transactions': [
			{
				'label': _('Activity'),
				'items': ['Timesheet']
			},
			{
				'label': _('Accounting'),
				'items': ['Expense Claim']
			},
			{
				'label': _('Reference'),
				'items': ['Stock Entry']
			}

		]
	}
