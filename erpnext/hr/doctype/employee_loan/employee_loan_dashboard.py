from frappe import _

def get_data():
	return {
		'fieldname': 'employee',
		'non_standard_fieldnames': {
			'Journal Entry': 'reference_name',
			},
		'transactions': [
			{
				'label': _('Employee'),
				'items': ['Employee Loan Application', 'Salary Slip']
			},
			{
				'label': _('Account'),
				'items': ['Journal Entry']
			}
		]
	}